from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import events, torrents, ws
from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.services.broadcaster import TorrentBroadcaster
from app.services.torrent_service import TorrentService
from app.services.worker import TorrentWorker
from app.torrent_engine.libtorrent_engine import LibtorrentEngine
from app.utils.rate_limit import InMemoryRateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.ensure_directories()
    await init_db()
    broadcaster = TorrentBroadcaster()
    engine = LibtorrentEngine(settings)
    service = TorrentService(settings, engine, broadcaster)
    app.state.broadcaster = broadcaster
    app.state.torrent_service = service

    async with SessionLocal() as db:
        await service.restore_active(db)

    worker = TorrentWorker(SessionLocal, service, settings)
    app.state.worker = worker
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()
        await engine.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="UWSLeech Authorized Torrent Manager",
        version="0.1.0",
        description="Local torrent management for legal, user-authorized torrents only.",
        lifespan=lifespan,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts + ["testserver"])
    if settings.public_rate_limit_per_minute > 0:
        app.add_middleware(
            InMemoryRateLimitMiddleware,
            requests_per_minute=settings.public_rate_limit_per_minute,
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(torrents.router)
    app.include_router(events.router)
    app.include_router(ws.router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
