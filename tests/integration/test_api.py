from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from app.api import events, torrents
from app.config import Settings
from app.db.models import Base
from app.db.session import get_db
from app.services.broadcaster import TorrentBroadcaster
from app.services.torrent_service import TorrentService
from app.torrent_engine.base import EngineTorrentFile
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.test_service import FakeEngine

pytestmark = pytest.mark.anyio


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
async def test_app(tmp_path: Path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_db():
        async with session_factory() as session:
            yield session

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        storage_root=tmp_path / "downloads",
        torrent_state_dir=tmp_path / "state",
        torrent_file_dir=tmp_path / "torrent-files",
    )
    settings.ensure_directories()
    app = FastAPI()
    app.state.broadcaster = TorrentBroadcaster()
    app.state.torrent_service = TorrentService(settings, FakeEngine(), app.state.broadcaster)
    app.dependency_overrides[get_db] = override_db
    app.include_router(torrents.router)
    app.include_router(events.router)
    yield app
    await engine.dispose()


async def test_create_and_list_magnet_via_api(test_app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/api/torrents/magnet",
            json={
                "magnet_uri": "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
                "category": "public-domain",
            },
        )
        assert create_response.status_code == 201

        list_response = await client.get("/api/torrents")
        assert list_response.status_code == 200
        payload = list_response.json()
        assert len(payload) == 1
        assert payload[0]["category"] == "public-domain"


async def test_remove_magnet_deletes_from_api_list(test_app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/api/torrents/magnet",
            json={
                "magnet_uri": "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
            },
        )
        task_id = create_response.json()["id"]

        remove_response = await client.post(f"/api/torrents/{task_id}/remove")
        list_response = await client.get("/api/torrents")

        assert remove_response.status_code == 204
        assert list_response.json() == []


async def test_stream_video_ranges_before_completion(test_app: FastAPI, monkeypatch) -> None:
    engine = test_app.state.torrent_service.engine
    payload = b"a video still downloading"
    reads = []

    async def files(task_id):
        return [EngineTorrentFile(index=0, path="movie.mkv", size=len(payload), progress=0.25)]

    async def read(task_id, file_index, offset, length):
        reads.append((offset, length))
        return payload[offset:offset + min(length, 4)]

    monkeypatch.setattr(engine, "get_files", files)
    monkeypatch.setattr(engine, "read_stream_chunk", read, raising=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        created = await client.post("/api/torrents/magnet", json={"magnet_uri": "magnet:?xt=test"})
        task_id = created.json()["id"]
        listing = (await client.get(f"/api/torrents/{task_id}/files")).json()
        assert listing[0]["download_url"] is None
        url = listing[0]["stream_url"]
        prepared = await client.post(url)
        assert prepared.json()["url"] == url
        assert engine.options[task_id].is_sequential
        assert prepared.json()["ready"] is True
        reads.clear()
        head = await client.head(url)
        assert head.status_code == 200
        assert int(head.headers["content-length"]) == len(payload)
        assert reads == []
        response = await client.get(url, headers={"Range": "bytes=3-13"})
        assert response.status_code == 206
        assert response.content == payload[3:14]
        assert response.headers["content-range"] == f"bytes 3-13/{len(payload)}"
        suffix = await client.get(url, headers={"Range": "bytes=-5"})
        assert suffix.content == payload[-5:]
        full = await client.get(url)
        assert full.status_code == 200
        assert full.content == payload
        invalid = await client.get(url, headers={"Range": "bytes=999-"})
        assert invalid.status_code == 416
        await client.post(f"/api/torrents/{task_id}/pause")
        assert (await client.get(url)).status_code == 409
        assert (await client.post(url)).status_code == 200

        async def unavailable(*args):
            raise TimeoutError

        monkeypatch.setattr(engine, "read_stream_chunk", unavailable)
        buffering = await client.post(url)
        assert buffering.status_code == 202
        assert buffering.json() == {"ready": False}
        assert (await client.get(url)).status_code == 503
