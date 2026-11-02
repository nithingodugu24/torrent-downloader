import httpx
import pytest
from app.main import create_app


@pytest.mark.anyio
async def test_built_ui_and_api_share_one_origin(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Torrent Downloader</h1>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/app.js").write_text("console.log('app')")
    app = create_app(frontend_dir=tmp_path)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Torrent Downloader" in response.text
        assert (await client.get("/assets/app.js")).status_code == 200
        assert (await client.get("/api/health")).json() == {
            "status": "ok",
            "app": "torrent-downloader",
        }
        assert (await client.get("/api/missing")).status_code == 404
        assert (await client.get("/../requirements.txt")).status_code == 404


@pytest.mark.anyio
async def test_api_still_available_without_frontend_build(tmp_path):
    app = create_app(frontend_dir=tmp_path)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/health")).status_code == 200
        assert (await client.get("/")).status_code == 404


@pytest.fixture()
def anyio_backend():
    return "asyncio"
