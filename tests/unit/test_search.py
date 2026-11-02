import json
from pathlib import Path

import httpx
import pytest
from app.api.search import router
from app.services import search
from fastapi import FastAPI

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "search"


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("provider", [name for name in search.BASES if name != "piratebay"])
def test_real_provider_markup(provider):
    results = search.parse_results(provider, (FIXTURES / f"{provider}.html").read_text())
    assert len(results) == 1
    result = results[0]
    assert result.title
    assert result.size
    assert result.seeds is not None
    assert result.leeches is not None
    assert result.url.startswith(search.BASES[provider])
    if provider != "limetorrents":
        assert result.magnet_uri and search.valid_magnet(result.magnet_uri)


def test_empty_and_blocked_pages_are_distinct():
    assert search.parse_results("bitsearch", "<h1>No results found</h1>") == []
    with pytest.raises(ValueError, match="blocked"):
        search.parse_results("bitsearch", "<h1>Verify you are human</h1>")


def test_external_links_are_not_returned():
    html = '<div class="torrent-result-card"><h3><a href="https://example.com/torrent/1">Bad</a></h3></div>'
    with pytest.raises(ValueError):
        search.parse_results("bitsearch", html)


@pytest.mark.anyio
async def test_search_keeps_successful_provider_results(monkeypatch):
    calls = []

    async def fetch(client, url, data=None):
        calls.append((url, data))
        if "uindex.org" in url:
            raise httpx.ConnectTimeout("timed out")
        if "apibay.org" in url:
            return (FIXTURES / "piratebay.json").read_text()
        name = (
            "torrentdownload"
            if "torrentdownload.info" in url
            else "bitsearch"
            if "bitsearch.eu" in url
            else "limetorrents"
        )
        return (FIXTURES / f"{name}.html").read_text()

    monkeypatch.setattr(search, "fetch_html", fetch)
    response = await search.search("ubuntu & linux", list(search.BASES), 1)
    assert len(response["results"]) == 4
    assert list(response["errors"]) == ["uindex"]
    assert "q=ubuntu+%26+linux" in calls[0][0]
    assert calls[2][1] == {"q": "ubuntu & linux"}


def test_torrentdownload_skips_ad_links_and_preserves_real_hash():
    html = (FIXTURES / "torrentdownload.html").read_text()
    ad = '<tr><td class="tt-name"><a href="/td.php?search=1">Fast download</a></td></tr>'
    results = search.parse_results("torrentdownload", html.replace("</table>", ad + "</table>"))
    assert len(results) == 1
    result = results[0]
    assert result.title == "Ubuntu 10 04 LTS x64"
    assert result.seeds == 4341 and result.leeches == 2956
    assert result.size == "697.57 MB"
    assert "A1425E0D6630336CDD9FB320F3FFF1030098975A" in result.magnet_uri
    assert search.valid_magnet(result.magnet_uri)
    assert search.search_url("torrentdownload", "ubuntu", 1) == (
        "https://www.torrentdownload.info/search?q=ubuntu"
    )
    assert search.search_url("torrentdownload", "ubuntu & linux", 2) == (
        "https://www.torrentdownload.info/search?q=ubuntu+%26+linux&p=2"
    )


@pytest.mark.anyio
async def test_torrentdownload_retries_a_transient_timeout(monkeypatch):
    calls = 0

    async def fetch(client, url, data=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("temporary timeout")
        return (FIXTURES / "torrentdownload.html").read_text()

    monkeypatch.setattr(search, "fetch_html", fetch)
    response = await search.search("ubuntu", ["torrentdownload"], 1)
    assert calls == 2
    assert len(response["results"]) == 1
    assert response["errors"] == {}


@pytest.mark.anyio
async def test_torrentdownload_retry_limit_keeps_other_results(monkeypatch):
    calls = 0

    async def fetch(client, url, data=None):
        nonlocal calls
        if "torrentdownload.info" in url:
            calls += 1
            raise httpx.ReadTimeout("offline")
        return (FIXTURES / "bitsearch.html").read_text()

    monkeypatch.setattr(search, "fetch_html", fetch)
    response = await search.search("ubuntu", ["torrentdownload", "bitsearch"], 1)
    assert calls == 3
    assert len(response["results"]) == 1
    assert list(response["errors"]) == ["torrentdownload"]


def test_piratebay_results_include_usable_magnet_and_counts():
    results = search.parse_piratebay((FIXTURES / "piratebay.json").read_text(), 1)
    assert len(results) == 1
    result = results[0]
    assert result.provider == "piratebay"
    assert result.title == "Ubuntu 22.04 LTS"
    assert result.seeds == 34 and result.leeches == 11
    assert result.size == "3.40 GiB"
    assert result.url == "https://thepiratebay.org/description.php?id=59191690"
    assert search.valid_magnet(result.magnet_uri)


def test_piratebay_empty_and_invalid_responses():
    assert search.parse_piratebay('[{"id":"0","name":"No results returned"}]', 1) == []
    assert search.parse_piratebay("[]", 1) == []
    with pytest.raises(ValueError):
        search.parse_piratebay("<h1>Blocked</h1>", 1)
    with pytest.raises(ValueError):
        search.parse_piratebay('{"error":"blocked"}', 1)
    assert search.parse_piratebay('[{"id":"1","name":"bad","info_hash":"invalid"}]', 1) == []


def test_piratebay_pagination_does_not_repeat_results():
    row = json.loads((FIXTURES / "piratebay.json").read_text())[0]
    payload = json.dumps(
        [{**row, "id": str(index + 1), "info_hash": f"{index + 1:040x}"} for index in range(100)]
    )
    first = search.parse_piratebay(payload, 1)
    second = search.parse_piratebay(payload, 2)
    assert len(first) == len(second) == 50
    assert not {result.url for result in first} & {result.url for result in second}
    assert search.parse_piratebay(payload, 3) == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/details.php?id=1",
        "https://uindex.org@localhost/details.php?id=1",
        "http://uindex.org/details.php?id=1",
        "https://uindex.org/redirect?url=http://localhost",
    ],
)
async def test_resolver_rejects_untrusted_urls(url):
    with pytest.raises(ValueError, match="Invalid"):
        await search.resolve_magnet("uindex", url)


@pytest.mark.anyio
async def test_resolver_extracts_magnet_without_executing_page(monkeypatch):
    magnet = "magnet:?xt=urn:btih:" + "a" * 40

    async def fetch(client, url, data=None):
        return f'<script>alert(1)</script><a href="{magnet}">Download</a>'

    monkeypatch.setattr(search, "fetch_html", fetch)
    assert (
        await search.resolve_magnet("limetorrents", "https://limetorrent.net/ubuntu-123.html")
        == magnet
    )


@pytest.mark.anyio
async def test_api_validation_and_response(monkeypatch):
    async def fake_search(q, providers, page):
        assert q == "ubuntu" and providers == ["bitsearch"]
        return {"results": [], "errors": {}, "page": page}

    monkeypatch.setattr(search, "search", fake_search)
    app = FastAPI()
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/search?q=ubuntu&provider=bitsearch")
        assert response.status_code == 200
        assert response.json() == {"results": [], "errors": {}, "page": 1}
        for query in ["q=", "q=%20", "q=x&provider=unknown", "q=x&page=0", "q=x&page=101"]:
            assert (await client.get(f"/api/search?{query}")).status_code == 422
        response = await client.post(
            "/api/search/resolve",
            json={
                "provider": "uindex",
                "url": "https://localhost/details.php?id=1",
            },
        )
        assert response.status_code == 400
