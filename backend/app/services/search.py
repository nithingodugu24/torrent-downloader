from __future__ import annotations

import asyncio
import json
import re
from typing import Literal
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

Provider = Literal["bitsearch", "uindex", "limetorrents", "piratebay", "torrentdownload"]
BASES = {
    "bitsearch": "https://bitsearch.eu",
    "uindex": "https://uindex.org",
    "limetorrents": "https://limetorrent.net",
    "piratebay": "https://thepiratebay.org",
    "torrentdownload": "https://www.torrentdownload.info",
}


class SearchResult(BaseModel):
    provider: Provider
    title: str
    url: str
    size: str | None = None
    seeds: int | None = None
    leeches: int | None = None
    magnet_uri: str | None = None


def search_url(provider: Provider, query: str, page: int) -> str:
    base = BASES[provider]
    if provider == "piratebay":
        return f"https://apibay.org/q.php?{urlencode({'q': query})}"
    if provider == "bitsearch":
        return f"{base}/search?{urlencode({'q': query, 'page': page})}"
    if provider == "torrentdownload":
        params: dict[str, str | int] = {"q": query}
        if page > 1:
            params["p"] = page
        return f"{base}/search?{urlencode(params)}"
    if provider == "uindex":
        return f"{base}/search.php?{urlencode({'search': query, 'c': 0, 'p': page})}"
    if page == 1:
        return f"{base}/search"
    return f"{base}/data.php?{urlencode({'q': query, 'page': page})}"


def valid_magnet(value: str) -> bool:
    return bool(re.search(r"(?:[?&])xt=urn:btih:(?:[a-fA-F0-9]{40}|[A-Z2-7]{32})(?:&|$)", value))


def parse_piratebay(payload: str, page: int) -> list[SearchResult]:
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("The Pirate Bay returned an unexpected response. Try again later.")
    results = []
    seen = set()

    def count(value: object) -> int | None:
        text = str(value)
        return int(text) if text.isdigit() else None

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("The Pirate Bay returned an unexpected result. Try again later.")
        if str(row.get("id")) == "0":  # The API's no-results sentinel.
            continue
        torrent_id = str(row.get("id", ""))
        name = row.get("name")
        info_hash = str(row.get("info_hash", "")).upper()
        if (
            not torrent_id.isdigit()
            or not isinstance(name, str)
            or not name.strip()
            or not re.fullmatch(r"[A-F0-9]{40}", info_hash)
            or info_hash == "0" * 40
            or info_hash in seen
        ):
            continue
        seen.add(info_hash)

        size = count(row.get("size"))
        size_text = None
        if size is not None:
            amount = float(size)
            for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
                size_text = f"{amount:.2f} {unit}"
                if amount < 1024 or unit == "TiB":
                    break
                amount /= 1024
        results.append(
            SearchResult(
                provider="piratebay",
                title=name.strip(),
                url=f"{BASES['piratebay']}/description.php?id={torrent_id}",
                size=size_text,
                seeds=count(row.get("seeders")),
                leeches=count(row.get("leechers")),
                magnet_uri=f"magnet:?xt=urn:btih:{info_hash}&{urlencode({'dn': name})}",
            )
        )
    # The API returns a capped result set; paginate that set without repeating it.
    return results[(page - 1) * 50 : page * 50]


def parse_results(provider: Provider, html: str) -> list[SearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(".torrent-result-card" if provider == "bitsearch" else "tr")
    results = []
    seen = set()
    for row in rows:
        if provider == "torrentdownload":
            title = next(
                (
                    link
                    for link in row.select(".tt-name a[href]")
                    if re.fullmatch(r"/[a-fA-F0-9]{40}/[^/]+", urlsplit(str(link["href"])).path)
                ),
                None,
            )
        else:
            title = None
        title = (
            title
            if provider == "torrentdownload"
            else row.select_one(
                "h3 a"
                if provider == "bitsearch"
                else (
                    'a[href*="details.php?id="]'
                    if provider == "uindex"
                    else '.tt-name a[href$=".html"]:not([rel="nofollow"])'
                )
            )
        )
        if title is None and provider == "limetorrents":
            title = row.select_one('.tt-name a[href*="-torrent-"]')
        if title is None:
            continue
        url = urljoin(BASES[provider], str(title.get("href", "")))
        if (
            urlsplit(url).scheme != "https"
            or urlsplit(url).netloc != urlsplit(BASES[provider]).netloc
            or url in seen
        ):
            continue
        seen.add(url)
        text = row.get_text(" ", strip=True)
        size = re.search(r"\b[\d.,]+\s*(?:[KMGT]i?B|bytes)\b", text, re.I)
        magnet = row.select_one('a[href^="magnet:?"]')
        uri = str(magnet["href"]) if magnet else ""
        if provider == "torrentdownload":
            info_hash = urlsplit(url).path.split("/")[1]
            name = urlencode({"dn": title.get_text(" ", strip=True)})
            uri = f"magnet:?xt=urn:btih:{info_hash}&{name}"
        seeds = leeches = None
        if provider == "bitsearch":
            seed_match = re.search(r"([\d,]+)\s+seeders", text)
            leech_match = re.search(r"([\d,]+)\s+leechers", text)
            seeds = int(seed_match[1].replace(",", "")) if seed_match else None
            leeches = int(leech_match[1].replace(",", "")) if leech_match else None
        else:
            cells = row.select("td")
            for attr, selector, fallback in [
                ("seeds", ".tdseed, .hp-td-seed", -2),
                ("leeches", ".tdleech, .hp-td-leech", -1),
            ]:
                cell = row.select_one(selector)
                if cell is None and len(cells) >= 4:
                    cell = cells[fallback]
                value = cell.get_text(strip=True).replace(",", "") if cell else ""
                number = int(value) if value.isdigit() else None
                if attr == "seeds":
                    seeds = number
                else:
                    leeches = number
        results.append(
            SearchResult(
                provider=provider,
                title=title.get_text(" ", strip=True),
                url=url,
                size=size[0] if size else None,
                seeds=seeds,
                leeches=leeches,
                magnet_uri=uri if valid_magnet(uri) else None,
            )
        )
    if not results and not re.search(
        r"no (?:torrents|results)|nothing found|0 results", soup.get_text(), re.I
    ):
        raise ValueError("Search page was blocked or its format changed. Try again later.")
    return results[:50]


async def fetch_html(client: httpx.AsyncClient, url: str, data: dict | None = None) -> str:
    # Fixed provider hosts only; redirects are deliberately not followed.
    headers = (
        {"Accept-Encoding": "identity", "Connection": "close"}
        if urlsplit(url).netloc == "www.torrentdownload.info"
        else None
    )
    async with client.stream(
        "POST" if data else "GET", url, data=data, headers=headers
    ) as response:
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError("Provider redirected the request. Try again later.")
        content = bytearray()
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content) > 3_000_000:
                raise ValueError("Provider response was too large.")
        return content.decode("utf-8", errors="replace")


async def search(query: str, providers: list[Provider], page: int) -> dict:
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Mozilla/5.0"}) as client:

        async def run(provider: Provider):
            try:
                async with asyncio.timeout(20):
                    attempts = 3 if provider == "torrentdownload" else 1
                    for attempt in range(attempts):
                        try:
                            async with asyncio.timeout(6 if attempts > 1 else 20):
                                html = await fetch_html(
                                    client,
                                    search_url(provider, query, page),
                                    {"q": query}
                                    if provider == "limetorrents" and page == 1
                                    else None,
                                )
                            break
                        except (httpx.RequestError, TimeoutError):
                            if attempt == attempts - 1:
                                raise
                if provider == "limetorrents" and page > 1:
                    if not html.strip():
                        return provider, [], None
                    html = f"<table>{html}</table>"
                if provider == "piratebay":
                    return provider, parse_piratebay(html, page), None
                return provider, parse_results(provider, html), None
            except httpx.HTTPStatusError as exc:
                return (
                    provider,
                    [],
                    f"Provider returned HTTP {exc.response.status_code}. Try again later.",
                )
            except (httpx.RequestError, TimeoutError):
                return (
                    provider,
                    [],
                    "Could not reach provider. Check your connection and try again.",
                )
            except ValueError as exc:
                return provider, [], str(exc)

        responses = await asyncio.gather(*(run(provider) for provider in dict.fromkeys(providers)))
    return {
        "results": [item for _, items, _ in responses for item in items],
        "errors": {provider: error for provider, _, error in responses if error},
        "page": page,
    }


async def resolve_magnet(provider: Provider, url: str) -> str:
    if provider in {"piratebay", "torrentdownload"}:
        raise ValueError("Search again to retrieve this result's magnet link.")
    parsed = urlsplit(url)
    allowed_path = (
        re.fullmatch(r"/torrent/[a-fA-F0-9]+", parsed.path)
        if provider == "bitsearch"
        else parsed.path == "/details.php" and parse_qs(parsed.query).get("id", [""])[0].isdigit()
        if provider == "uindex"
        else re.fullmatch(r"/[\w-]+-\d+\.html", parsed.path)
    )
    if (
        parsed.scheme != "https"
        or parsed.netloc != urlsplit(BASES[provider]).netloc
        or not allowed_path
    ):
        raise ValueError("Invalid provider detail URL.")
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Mozilla/5.0"}) as client:
        async with asyncio.timeout(20):
            html = await fetch_html(client, url)
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select('a[href^="magnet:?"]'):
        uri = str(link["href"])
        if valid_magnet(uri):
            return uri
    raise ValueError("No magnet link found on this result. Try opening the source page.")
