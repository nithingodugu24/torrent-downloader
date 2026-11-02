from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import TaskEvent, TorrentTask
from app.schemas.torrent import TorrentPatch
from app.services.broadcaster import TorrentBroadcaster
from app.torrent_engine.base import (
    EngineTorrentFile,
    EngineTorrentOptions,
    EngineTorrentStatus,
    TorrentEngine,
)
from app.utils.paths import safe_resolve_under_root, safe_torrent_filename
from app.utils.time import utcnow

REFRESHED_STATUSES = {"queued", "metadata", "downloading", "seeding"}
RESTORED_STATUSES = REFRESHED_STATUSES | {"paused"}
PAUSED_STATUS = "paused"
STOPPED_STATUS = "stopped"


class TorrentService:
    def __init__(
        self, settings: Settings, engine: TorrentEngine, broadcaster: TorrentBroadcaster
    ) -> None:
        self.settings = settings
        self.engine = engine
        self.broadcaster = broadcaster
        self._locks: dict[str, asyncio.Lock] = {}

    async def add_magnet(
        self,
        db: AsyncSession,
        magnet_uri: str,
        save_path: str | None,
        category: str | None,
        priority: int,
        is_sequential: bool,
    ) -> TorrentTask:
        task_id = str(uuid4())
        resolved_save_path = safe_resolve_under_root(self.settings.storage_root, save_path)
        resolved_save_path.mkdir(parents=True, exist_ok=True)
        task = TorrentTask(
            id=task_id,
            name="Magnet metadata pending",
            magnet_uri=magnet_uri,
            save_path=str(resolved_save_path),
            status="queued",
            category=category,
            priority=priority,
            is_sequential=is_sequential,
        )
        db.add(task)
        await db.flush()
        await self._event(db, task.id, "info", "created", "Magnet task created.")
        try:
            engine_status = await self.engine.add_magnet(
                task.id,
                magnet_uri,
                resolved_save_path,
                self._options_from_task(task),
            )
            self._apply_status(task, engine_status)
        except Exception as exc:
            task.status = "errored"
            task.error_message = str(exc)
            await self._event(db, task.id, "error", "engine", str(exc))
        await db.commit()
        await db.refresh(task)
        await self._publish_task(task, "created")
        return task

    async def add_torrent_file(
        self,
        db: AsyncSession,
        filename: str,
        content: bytes,
        save_path: str | None,
        category: str | None,
        priority: int,
        is_sequential: bool,
    ) -> TorrentTask:
        if not filename.endswith(".torrent"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload a .torrent file.",
            )
        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if not content or len(content) > max_bytes:
            detail = (
                ".torrent file must be non-empty and at most "
                f"{self.settings.max_upload_size_mb} MB."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )
        if not content.startswith(b"d"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file does not look like a bencoded .torrent file.",
            )

        task_id = str(uuid4())
        torrent_file = self.settings.torrent_file_dir / safe_torrent_filename(task_id)
        torrent_file.write_bytes(content)
        resolved_save_path = safe_resolve_under_root(self.settings.storage_root, save_path)
        resolved_save_path.mkdir(parents=True, exist_ok=True)
        task = TorrentTask(
            id=task_id,
            name=filename.removesuffix(".torrent"),
            torrent_file_path=str(torrent_file),
            save_path=str(resolved_save_path),
            status="queued",
            category=category,
            priority=priority,
            is_sequential=is_sequential,
        )
        db.add(task)
        await db.flush()
        await self._event(db, task.id, "info", "created", ".torrent task created.")
        try:
            engine_status = await self.engine.add_torrent_file(
                task.id,
                torrent_file,
                resolved_save_path,
                self._options_from_task(task),
            )
            self._apply_status(task, engine_status)
        except Exception as exc:
            task.status = "errored"
            task.error_message = str(exc)
            await self._event(db, task.id, "error", "engine", str(exc))
        await db.commit()
        await db.refresh(task)
        await self._publish_task(task, "created")
        return task

    async def list_tasks(
        self,
        db: AsyncSession,
        status_filter: str | None = None,
        search: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> list[TorrentTask]:
        stmt: Select[tuple[TorrentTask]] = select(TorrentTask)
        if status_filter:
            stmt = stmt.where(TorrentTask.status == status_filter)
        if search:
            stmt = stmt.where(TorrentTask.name.ilike(f"%{search}%"))
        sort_column = getattr(TorrentTask, sort, TorrentTask.created_at)
        stmt = stmt.order_by(sort_column.asc() if order == "asc" else sort_column.desc())
        return list((await db.scalars(stmt)).all())

    async def get_task(self, db: AsyncSession, task_id: str) -> TorrentTask:
        task = await db.get(TorrentTask, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torrent task not found.",
            )
        return task

    async def update_task(self, db: AsyncSession, task_id: str, patch: TorrentPatch) -> TorrentTask:
        task = await self.get_task(db, task_id)
        async with self._lock_for(task_id):
            data = patch.model_dump(exclude_unset=True)
            if "save_path" in data and data["save_path"] is not None:
                task.save_path = str(
                    safe_resolve_under_root(self.settings.storage_root, data["save_path"])
                )
            for field, value in data.items():
                if field == "save_path":
                    continue
                setattr(task, field, value)
            await self.engine.apply_options(task.id, self._options_from_task(task))
            await self._event(db, task.id, "info", "updated", "Task settings updated.")
            await db.commit()
            await db.refresh(task)
            await self._publish_task(task, "updated")
            return task

    async def action(
        self, db: AsyncSession, task_id: str, action: str, delete_files: bool = False
    ) -> TorrentTask:
        task = await self.get_task(db, task_id)
        async with self._lock_for(task_id):
            try:
                if action == "start":
                    await self._restore_if_needed(task)
                    await self.engine.start(task.id)
                    task.status = "downloading"
                elif action == "pause":
                    await self.engine.pause(task.id)
                    task.status = "paused"
                    task.download_speed = 0
                    task.upload_speed = 0
                elif action == "resume":
                    await self._restore_if_needed(task)
                    await self.engine.resume(task.id)
                    task.status = "downloading"
                elif action == "stop":
                    await self.engine.stop(task.id)
                    task.status = "stopped"
                    task.download_speed = 0
                    task.upload_speed = 0
                elif action == "remove":
                    await self.engine.remove(task.id, delete_files=delete_files)
                    task.status = "stopped"
                    task.error_message = None
                    await self._publish_task(task, "removed")
                    await db.delete(task)
                    await db.commit()
                    return task
                elif action == "recheck":
                    await self._restore_if_needed(task)
                    await self.engine.recheck(task.id)
                    task.status = "queued"
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unknown action.",
                    )
                task.error_message = None
                await self._event(db, task.id, "info", action, f"Task {action} requested.")
            except KeyError:
                if action in {"pause", "stop", "remove"}:
                    task.status = "stopped"
                    if action == "remove":
                        await self._publish_task(task, "removed")
                        await db.delete(task)
                        await db.commit()
                        return task
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Torrent is not currently loaded in the engine.",
                    ) from None
            except Exception as exc:
                task.status = "errored"
                task.error_message = str(exc)
                await self._event(db, task.id, "error", action, str(exc))
            await db.commit()
            await db.refresh(task)
            await self._publish_task(task, action)
            return task

    async def get_files(self, db: AsyncSession, task_id: str) -> list[EngineTorrentFile]:
        await self.get_task(db, task_id)
        try:
            return await self.engine.get_files(task_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Torrent is not currently loaded in the engine.",
            ) from exc

    async def list_events(self, db: AsyncSession, task_id: str | None = None) -> list[TaskEvent]:
        stmt = select(TaskEvent)
        if task_id:
            stmt = stmt.where(TaskEvent.task_id == task_id)
        stmt = stmt.order_by(TaskEvent.created_at.desc()).limit(500)
        return list((await db.scalars(stmt)).all())

    async def restore_active(self, db: AsyncSession) -> None:
        stmt = select(TorrentTask).where(TorrentTask.status.in_(RESTORED_STATUSES))
        tasks = list(
            (
                await db.scalars(stmt)
            ).all()
        )
        for task in tasks:
            try:
                was_paused = task.status == "paused"
                status_update = await self.engine.restore(
                    task.id,
                    task.magnet_uri,
                    Path(task.torrent_file_path) if task.torrent_file_path else None,
                    Path(task.save_path),
                    self._options_from_task(task),
                )
                self._apply_status(task, status_update)
                if was_paused:
                    await self.engine.pause(task.id)
                    task.status = "paused"
                    task.download_speed = 0
                    task.upload_speed = 0
                await self._event(db, task.id, "info", "restore", "Task restored on startup.")
            except Exception as exc:
                task.status = "errored"
                task.error_message = str(exc)
                await self._event(db, task.id, "error", "restore", str(exc))
        await db.commit()

    async def refresh_all(self, db: AsyncSession) -> None:
        await self._enforce_paused_tasks(db)
        await self._unload_stopped_tasks(db)
        stmt = select(TorrentTask).where(TorrentTask.status.in_(REFRESHED_STATUSES))
        tasks = list(
            (
                await db.scalars(stmt)
            ).all()
        )
        for task in tasks:
            async with self._lock_for(task.id):
                try:
                    status_update = await self.engine.get_status(task.id)
                    previous_status = task.status
                    self._apply_status(task, status_update)
                    if task.status in {"completed", "seeding"} and not task.completed_at:
                        task.completed_at = utcnow()
                        await self._event(db, task.id, "info", "completed", "Torrent completed.")
                    if previous_status != task.status:
                        await self._event(
                            db, task.id, "info", "status", f"Status changed to {task.status}."
                        )
                    resume_data = await self.engine.save_resume_data(task.id)
                    if resume_data:
                        resume_path = self.settings.torrent_state_dir / f"{task.id}.resume"
                        resume_path.write_bytes(resume_data)
                    await self._publish_task(task, "progress")
                except KeyError:
                    continue
                except Exception as exc:
                    task.status = "errored"
                    task.error_message = str(exc)
                    await self._event(db, task.id, "error", "refresh", str(exc))
        await db.commit()

    async def _enforce_paused_tasks(self, db: AsyncSession) -> None:
        tasks = list(
            (
                await db.scalars(select(TorrentTask).where(TorrentTask.status == PAUSED_STATUS))
            ).all()
        )
        for task in tasks:
            async with self._lock_for(task.id):
                try:
                    await self.engine.pause(task.id)
                except KeyError:
                    continue
                task.status = "paused"
                task.download_speed = 0
                task.upload_speed = 0
                await self._publish_task(task, "paused")

    async def _unload_stopped_tasks(self, db: AsyncSession) -> None:
        tasks = list(
            (
                await db.scalars(select(TorrentTask).where(TorrentTask.status == STOPPED_STATUS))
            ).all()
        )
        for task in tasks:
            async with self._lock_for(task.id):
                try:
                    await self.engine.remove(task.id, delete_files=False)
                except KeyError:
                    continue

    async def _restore_if_needed(self, task: TorrentTask) -> None:
        try:
            await self.engine.get_status(task.id)
            return
        except KeyError:
            pass
        status_update = await self.engine.restore(
            task.id,
            task.magnet_uri,
            Path(task.torrent_file_path) if task.torrent_file_path else None,
            Path(task.save_path),
            self._options_from_task(task),
        )
        self._apply_status(task, status_update)

    def _options_from_task(self, task: TorrentTask) -> EngineTorrentOptions:
        return EngineTorrentOptions(
            priority=task.priority,
            download_limit=task.download_limit,
            upload_limit=task.upload_limit,
            seed_limit=task.seed_limit,
            max_connections=task.max_connections,
            is_sequential=task.is_sequential,
        )

    def _apply_status(self, task: TorrentTask, status_update: EngineTorrentStatus) -> None:
        task.name = status_update.name or task.name
        task.info_hash = status_update.info_hash or task.info_hash
        task.status = status_update.status
        task.progress = max(0.0, min(1.0, status_update.progress))
        task.download_speed = status_update.download_speed
        task.upload_speed = status_update.upload_speed
        task.ratio = status_update.ratio
        task.total_size = status_update.total_size
        task.downloaded = status_update.downloaded
        task.uploaded = status_update.uploaded
        task.peers = status_update.peers
        task.seeds = status_update.seeds
        task.error_message = status_update.error_message

    async def _event(
        self, db: AsyncSession, task_id: str | None, level: str, event_type: str, message: str
    ) -> None:
        db.add(
            TaskEvent(
                task_id=task_id,
                level=level,
                event_type=event_type,
                message=message[:2000],
            )
        )

    async def _publish_task(self, task: TorrentTask, event: str) -> None:
        await self.broadcaster.publish(
            {
                "event": event,
                "task": {
                    "id": task.id,
                    "name": task.name,
                    "status": task.status,
                    "progress": task.progress,
                    "download_speed": task.download_speed,
                    "upload_speed": task.upload_speed,
                    "total_size": task.total_size,
                    "downloaded": task.downloaded,
                    "uploaded": task.uploaded,
                    "ratio": task.ratio,
                    "peers": task.peers,
                    "seeds": task.seeds,
                    "error_message": task.error_message,
                },
            }
        )

    def _lock_for(self, task_id: str) -> asyncio.Lock:
        lock = self._locks.get(task_id)
        if not lock:
            lock = asyncio.Lock()
            self._locks[task_id] = lock
        return lock
