from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.config import Settings
from app.torrent_engine.base import EngineTorrentFile, EngineTorrentOptions, EngineTorrentStatus
from app.utils.paths import safe_resolve_under_root

logger = logging.getLogger(__name__)


class LibtorrentEngine:
    def __init__(self, settings: Settings) -> None:
        try:
            import libtorrent as lt
        except ImportError as exc:
            raise RuntimeError(
                "python-libtorrent is required for runtime. Install libtorrent for your platform "
                "before starting the server."
            ) from exc

        self._lt = lt
        self._settings = settings
        self._session = lt.session()
        self._handles: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._configure_session()

    def _configure_session(self) -> None:
        settings_pack: dict[str, Any] = {
            "active_downloads": self._settings.max_active_downloads,
            "active_seeds": self._settings.max_active_seeds,
        }
        if self._settings.global_download_limit > 0:
            settings_pack["download_rate_limit"] = self._settings.global_download_limit
        if self._settings.global_upload_limit > 0:
            settings_pack["upload_rate_limit"] = self._settings.global_upload_limit
        try:
            self._session.apply_settings(settings_pack)  # type: ignore[arg-type]
        except AttributeError:
            for key, value in settings_pack.items():
                setter = getattr(self._session, f"set_{key}", None)
                if setter:
                    setter(value)

    async def add_magnet(
        self, task_id: str, magnet_uri: str, save_path: Path, options: EngineTorrentOptions
    ) -> EngineTorrentStatus:
        async with self._lock:
            params = self._lt.parse_magnet_uri(magnet_uri)
            params.save_path = str(save_path)
            handle = self._session.add_torrent(params)
            self._handles[task_id] = handle
            await self.apply_options(task_id, options)
            return self._status_from_handle(task_id, handle)

    async def add_torrent_file(
        self, task_id: str, torrent_file: Path, save_path: Path, options: EngineTorrentOptions
    ) -> EngineTorrentStatus:
        async with self._lock:
            info = self._lt.torrent_info(str(torrent_file))
            params = self._lt.add_torrent_params()
            params.ti = info
            params.save_path = str(save_path)
            handle = self._session.add_torrent(params)
            self._handles[task_id] = handle
            await self.apply_options(task_id, options)
            return self._status_from_handle(task_id, handle)

    async def restore(
        self,
        task_id: str,
        magnet_uri: str | None,
        torrent_file: Path | None,
        save_path: Path,
        options: EngineTorrentOptions,
    ) -> EngineTorrentStatus:
        if torrent_file is not None:
            exists = await asyncio.to_thread(lambda: torrent_file.exists())
            if exists:
                return await self.add_torrent_file(task_id, torrent_file, save_path, options)
        if magnet_uri:
            return await self.add_magnet(task_id, magnet_uri, save_path, options)
        return EngineTorrentStatus(
            task_id=task_id,
            status="errored",
            error_message="No torrent source",
        )

    async def start(self, task_id: str) -> None:
        await self.resume(task_id)

    async def pause(self, task_id: str) -> None:
        handle = self._require_handle(task_id)
        self._disable_auto_managed(handle)
        handle.pause()

    async def resume(self, task_id: str) -> None:
        handle = self._require_handle(task_id)
        self._enable_auto_managed(handle)
        handle.resume()

    async def stop(self, task_id: str) -> None:
        await self.remove(task_id, delete_files=False)

    async def remove(self, task_id: str, delete_files: bool = False) -> None:
        async with self._lock:
            handle = self._handles.pop(task_id, None)
            if not handle:
                return
            flags = 0
            if delete_files:
                flags = getattr(self._lt.options_t, "delete_files", 1)
            self._session.remove_torrent(handle, flags)

    async def recheck(self, task_id: str) -> None:
        self._require_handle(task_id).force_recheck()

    async def apply_options(self, task_id: str, options: EngineTorrentOptions) -> None:
        handle = self._require_handle(task_id)
        if options.download_limit is not None:
            handle.set_download_limit(options.download_limit)
        if options.upload_limit is not None:
            handle.set_upload_limit(options.upload_limit)
        if options.max_connections is not None:
            handle.set_max_connections(options.max_connections)
        try:
            handle.set_sequential_download(options.is_sequential)
        except AttributeError:
            pass
        try:
            file_count = handle.torrent_file().num_files() if handle.has_metadata() else 0
            if file_count:
                handle.prioritize_files([options.priority] * file_count)
        except RuntimeError:
            pass

    async def get_status(self, task_id: str) -> EngineTorrentStatus:
        return self._status_from_handle(task_id, self._require_handle(task_id))

    async def get_files(self, task_id: str) -> list[EngineTorrentFile]:
        handle = self._require_handle(task_id)
        if not handle.has_metadata():
            return []
        info = handle.torrent_file()
        priorities = list(handle.file_priorities()) if hasattr(handle, "file_priorities") else []
        progress: list[int] = []
        try:
            progress = list(handle.file_progress())
        except RuntimeError:
            progress = []
        files: list[EngineTorrentFile] = []
        storage = info.files()
        for index in range(storage.num_files()):
            path = storage.file_path(index)
            size = int(storage.file_size(index))
            done = progress[index] if index < len(progress) else 0
            priority = priorities[index] if index < len(priorities) else 4
            files.append(
                EngineTorrentFile(
                    index=index,
                    path=path,
                    size=size,
                    progress=(done / size) if size else 1.0,
                    priority=priority,
                )
            )
        return files

    async def read_stream_chunk(
        self, task_id: str, file_index: int, offset: int, length: int
    ) -> bytes:
        handle = self._require_handle(task_id)
        info = handle.torrent_file()
        storage = info.files()
        size = int(storage.file_size(file_index))
        piece_length = int(info.piece_length())
        absolute = int(storage.file_offset(file_index)) + offset
        piece = absolute // piece_length
        length = min(length, size - offset, piece_length - absolute % piece_length, 256 * 1024)
        if offset < 0 or length <= 0:
            raise ValueError("Invalid stream offset.")
        path = safe_resolve_under_root(
            Path(handle.status().save_path), storage.file_path(file_index)
        )
        # Only verified, disk-written pieces may be read: sparse files can contain holes.
        last_piece = (int(storage.file_offset(file_index)) + size - 1) // piece_length
        window = min(32, max(1, (8 * 1024 * 1024) // piece_length))
        deadlines = range(piece, min(last_piece + 1, piece + window))
        try:
            handle.file_priority(file_index, max(1, handle.file_priority(file_index)))
            for ahead in deadlines:
                if not handle.have_piece(ahead):
                    handle.set_piece_deadline(ahead, (ahead - piece) * 250)
            async with asyncio.timeout(120):
                while True:
                    current = self._require_handle(task_id)
                    if not current.is_valid() or (
                        self._map_state(current.status(), current) == "paused"
                    ):
                        raise RuntimeError("Torrent was paused or removed during playback.")
                    if current.have_piece(piece):
                        break
                    await asyncio.sleep(0.2)
                def read() -> bytes:
                    with path.open("rb") as source:
                        source.seek(offset)
                        return source.read(length)

                data = await asyncio.to_thread(read)
                if len(data) != length:
                    raise RuntimeError("Downloaded video data is unavailable.")
                return data
        finally:
            if handle.is_valid():
                for ahead in deadlines:
                    handle.reset_piece_deadline(ahead)

    async def save_resume_data(self, task_id: str) -> bytes | None:
        handle = self._handles.get(task_id)
        if not handle or not handle.is_valid():
            return None
        try:
            handle.save_resume_data()
            pop_alert = getattr(self._session, "pop_alert", None)
            if pop_alert is None:
                pop_alerts = getattr(self._session, "pop_alerts", None)
                if pop_alerts is None:
                    return None
                pop_alert = _first_alert(pop_alerts)
            for _ in range(20):
                alert = pop_alert()
                if not alert:
                    await asyncio.sleep(0.05)
                    continue
                if alert.__class__.__name__ == "save_resume_data_alert":
                    return bytes(self._lt.write_resume_data_buf(alert.params))
                if alert.__class__.__name__ == "save_resume_data_failed_alert":
                    return None
        except Exception:
            return None
        return None

    async def close(self) -> None:
        for task_id in list(self._handles):
            try:
                await self.pause(task_id)
            except Exception:
                logger.debug("Failed to pause torrent during engine shutdown.", exc_info=True)
                continue

    def _require_handle(self, task_id: str) -> Any:
        handle = self._handles.get(task_id)
        if not handle:
            raise KeyError(f"Torrent task {task_id} is not loaded in the engine.")
        return handle

    def _disable_auto_managed(self, handle: Any) -> None:
        flags = getattr(self._lt, "torrent_flags", None)
        auto_managed = getattr(flags, "auto_managed", None)
        if auto_managed is None:
            return
        try:
            handle.unset_flags(auto_managed)
        except AttributeError:
            pass

    def _enable_auto_managed(self, handle: Any) -> None:
        flags = getattr(self._lt, "torrent_flags", None)
        auto_managed = getattr(flags, "auto_managed", None)
        if auto_managed is None:
            return
        try:
            handle.set_flags(auto_managed)
        except AttributeError:
            pass

    def _status_from_handle(self, task_id: str, handle: Any) -> EngineTorrentStatus:
        status = handle.status()
        info_hash = None
        try:
            info_hash = str(handle.info_hash())
        except RuntimeError:
            pass

        total_done = int(getattr(status, "total_done", 0) or 0)
        total_wanted = int(getattr(status, "total_wanted", 0) or 0)
        uploaded = int(getattr(status, "total_upload", 0) or 0)
        ratio = (uploaded / total_done) if total_done else 0.0
        state = self._map_state(status, handle)

        return EngineTorrentStatus(
            task_id=task_id,
            name=str(getattr(status, "name", "") or ""),
            info_hash=info_hash,
            status=state,
            progress=float(getattr(status, "progress", 0.0) or 0.0),
            download_speed=int(getattr(status, "download_rate", 0) or 0),
            upload_speed=int(getattr(status, "upload_rate", 0) or 0),
            ratio=ratio,
            total_size=total_wanted,
            downloaded=total_done,
            uploaded=uploaded,
            peers=int(getattr(status, "num_peers", 0) or 0),
            seeds=int(getattr(status, "num_seeds", 0) or 0),
            error_message=str(getattr(status, "error", "") or "") or None,
            tracker_status=self._tracker_status(handle),
        )

    def _map_state(self, status: Any, handle: Any) -> str:
        if getattr(status, "error", None):
            return "errored"
        if getattr(status, "paused", False):
            flags = getattr(status, "flags", 0)
            auto_managed = getattr(self._lt.torrent_flags, "auto_managed", 0)
            if flags & auto_managed:
                return "queued"
            return "paused"
        if not handle.has_metadata():
            return "metadata"
        if getattr(status, "is_seeding", False):
            return "seeding"
        if float(getattr(status, "progress", 0.0) or 0.0) >= 1.0:
            return "completed"
        return "downloading"

    def _tracker_status(self, handle: Any) -> list[str]:
        try:
            return [tracker.get("url", "") for tracker in handle.trackers() if tracker.get("url")]
        except Exception:
            return []


def _first_alert(pop_alerts: Callable[[], list[Any]]) -> Callable[[], Any | None]:
    def pop_one() -> Any | None:
        alerts = pop_alerts()
        return alerts[0] if alerts else None

    return pop_one
