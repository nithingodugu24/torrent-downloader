from __future__ import annotations

from pathlib import Path

import pytest
from app.config import Settings
from app.db.models import Base, TorrentTask
from app.services.broadcaster import TorrentBroadcaster
from app.services.torrent_service import TorrentService
from app.torrent_engine.base import EngineTorrentFile, EngineTorrentOptions, EngineTorrentStatus
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytestmark = pytest.mark.anyio


class FakeEngine:
    def __init__(self) -> None:
        self.statuses: dict[str, EngineTorrentStatus] = {}
        self.options: dict[str, EngineTorrentOptions] = {}
        self.removed: set[str] = set()
        self.pause_calls: dict[str, int] = {}

    async def add_magnet(
        self, task_id: str, magnet_uri: str, save_path: Path, options: EngineTorrentOptions
    ) -> EngineTorrentStatus:
        self.options[task_id] = options
        status = EngineTorrentStatus(
            task_id=task_id,
            name="Legal test torrent",
            info_hash="0123456789012345678901234567890123456789",
            status="downloading",
            progress=0.25,
            total_size=100,
            downloaded=25,
            peers=2,
            seeds=1,
        )
        self.statuses[task_id] = status
        return status

    async def add_torrent_file(
        self, task_id: str, torrent_file: Path, save_path: Path, options: EngineTorrentOptions
    ) -> EngineTorrentStatus:
        return await self.add_magnet(task_id, "file", save_path, options)

    async def restore(
        self,
        task_id: str,
        magnet_uri: str | None,
        torrent_file: Path | None,
        save_path: Path,
        options: EngineTorrentOptions,
    ) -> EngineTorrentStatus:
        return await self.add_magnet(task_id, magnet_uri or "file", save_path, options)

    async def start(self, task_id: str) -> None:
        self.statuses[task_id].status = "downloading"

    async def pause(self, task_id: str) -> None:
        if task_id not in self.statuses:
            raise KeyError(task_id)
        self.pause_calls[task_id] = self.pause_calls.get(task_id, 0) + 1
        self.statuses[task_id].status = "paused"

    async def resume(self, task_id: str) -> None:
        if task_id not in self.statuses:
            raise KeyError(task_id)
        self.statuses[task_id].status = "downloading"

    async def stop(self, task_id: str) -> None:
        await self.remove(task_id, delete_files=False)

    async def remove(self, task_id: str, delete_files: bool = False) -> None:
        self.removed.add(task_id)
        self.statuses.pop(task_id, None)

    async def recheck(self, task_id: str) -> None:
        self.statuses[task_id].status = "queued"

    async def apply_options(self, task_id: str, options: EngineTorrentOptions) -> None:
        self.options[task_id] = options

    async def get_status(self, task_id: str) -> EngineTorrentStatus:
        if task_id not in self.statuses:
            raise KeyError(task_id)
        status = self.statuses[task_id]
        status.progress = min(1.0, status.progress + 0.5)
        status.downloaded = int(status.total_size * status.progress)
        if status.progress >= 1.0:
            status.status = "completed"
        return status

    async def get_files(self, task_id: str) -> list[EngineTorrentFile]:
        return [EngineTorrentFile(index=0, path="legal-file.txt", size=100, progress=1.0)]

    async def save_resume_data(self, task_id: str) -> bytes | None:
        return b"resume"

    async def close(self) -> None:
        return None


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
async def service_stack(tmp_path: Path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        storage_root=tmp_path / "downloads",
        torrent_state_dir=tmp_path / "state",
        torrent_file_dir=tmp_path / "torrent-files",
    )
    settings.ensure_directories()
    fake_engine = FakeEngine()
    service = TorrentService(settings, fake_engine, TorrentBroadcaster())
    yield async_session, service, fake_engine
    await engine.dispose()


async def test_add_pause_resume_and_event_log(service_stack) -> None:
    session_factory, service, fake_engine = service_stack
    async with session_factory() as db:
        task = await service.add_magnet(
            db,
            "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
            None,
            "public-domain",
            4,
            False,
        )
        assert task.status == "downloading"

        paused = await service.action(db, task.id, "pause")
        assert paused.status == "paused"

        resumed = await service.action(db, task.id, "resume")
        assert resumed.status == "downloading"

        events = await service.list_events(db, task.id)
        assert {event.event_type for event in events} >= {"created", "pause", "resume"}
        assert task.id in fake_engine.options


async def test_refresh_persists_completion_and_resume_data(service_stack, tmp_path: Path) -> None:
    session_factory, service, _fake_engine = service_stack
    async with session_factory() as db:
        task = await service.add_magnet(
            db,
            "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
            None,
            None,
            4,
            False,
        )
        await service.refresh_all(db)
        await service.refresh_all(db)
        refreshed = await db.get(TorrentTask, task.id)

        assert refreshed is not None
        assert refreshed.status == "completed"
        assert (service.settings.torrent_state_dir / f"{task.id}.resume").exists()


async def test_paused_task_is_not_overwritten_by_refresh(service_stack) -> None:
    session_factory, service, fake_engine = service_stack
    async with session_factory() as db:
        task = await service.add_magnet(
            db,
            "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
            None,
            None,
            4,
            False,
        )
        await service.action(db, task.id, "pause")
        fake_engine.statuses[task.id].status = "downloading"

        await service.refresh_all(db)
        refreshed = await db.get(TorrentTask, task.id)

        assert refreshed is not None
        assert refreshed.status == "paused"
        assert fake_engine.pause_calls[task.id] >= 2


async def test_stop_unloads_task_and_prevents_refresh_restart(service_stack) -> None:
    session_factory, service, fake_engine = service_stack
    async with session_factory() as db:
        task = await service.add_magnet(
            db,
            "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
            None,
            None,
            4,
            False,
        )

        stopped = await service.action(db, task.id, "stop")
        await service.refresh_all(db)
        refreshed = await db.get(TorrentTask, task.id)

        assert stopped.status == "stopped"
        assert refreshed is not None
        assert refreshed.status == "stopped"
        assert task.id in fake_engine.removed
        assert task.id not in fake_engine.statuses


async def test_start_after_stop_restores_engine_handle(service_stack) -> None:
    session_factory, service, fake_engine = service_stack
    async with session_factory() as db:
        task = await service.add_magnet(
            db,
            "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
            None,
            None,
            4,
            False,
        )
        await service.action(db, task.id, "stop")

        started = await service.action(db, task.id, "start")

        assert started.status == "downloading"
        assert task.id in fake_engine.statuses


async def test_refresh_unloads_legacy_stopped_handle(service_stack) -> None:
    session_factory, service, fake_engine = service_stack
    async with session_factory() as db:
        task = await service.add_magnet(
            db,
            "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
            None,
            None,
            4,
            False,
        )
        task.status = "stopped"
        await db.commit()

        await service.refresh_all(db)

        assert task.id in fake_engine.removed
        assert task.id not in fake_engine.statuses


async def test_remove_deletes_task_record(service_stack) -> None:
    session_factory, service, fake_engine = service_stack
    async with session_factory() as db:
        task = await service.add_magnet(
            db,
            "magnet:?xt=urn:btih:0123456789012345678901234567890123456789",
            None,
            None,
            4,
            False,
        )

        removed = await service.action(db, task.id, "remove")
        missing = await db.get(TorrentTask, task.id)

        assert removed.status == "stopped"
        assert missing is None
        assert task.id in fake_engine.removed
