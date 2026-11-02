from __future__ import annotations

import asyncio
import contextlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.services.torrent_service import TorrentService

logger = logging.getLogger(__name__)


class TorrentWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        service: TorrentService,
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.service = service
        self.settings = settings
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="torrent-worker")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                async with self.session_factory() as db:
                    await self.service.refresh_all(db)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Torrent worker refresh failed.")
            await asyncio.sleep(self.settings.websocket_interval_seconds)
