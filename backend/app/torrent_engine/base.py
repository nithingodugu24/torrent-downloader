from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class EngineTorrentOptions:
    priority: int = 4
    download_limit: int | None = None
    upload_limit: int | None = None
    seed_limit: float | None = None
    max_connections: int | None = None
    is_sequential: bool = False


@dataclass(slots=True)
class EngineTorrentFile:
    index: int
    path: str
    size: int
    progress: float = 0.0
    priority: int = 4


@dataclass(slots=True)
class EngineTorrentStatus:
    task_id: str
    name: str = ""
    info_hash: str | None = None
    status: str = "queued"
    progress: float = 0.0
    download_speed: int = 0
    upload_speed: int = 0
    ratio: float = 0.0
    total_size: int = 0
    downloaded: int = 0
    uploaded: int = 0
    peers: int = 0
    seeds: int = 0
    error_message: str | None = None
    tracker_status: list[str] = field(default_factory=list)


class TorrentEngine(Protocol):
    async def add_magnet(
        self, task_id: str, magnet_uri: str, save_path: Path, options: EngineTorrentOptions
    ) -> EngineTorrentStatus:
        ...

    async def add_torrent_file(
        self, task_id: str, torrent_file: Path, save_path: Path, options: EngineTorrentOptions
    ) -> EngineTorrentStatus:
        ...

    async def restore(
        self,
        task_id: str,
        magnet_uri: str | None,
        torrent_file: Path | None,
        save_path: Path,
        options: EngineTorrentOptions,
    ) -> EngineTorrentStatus:
        ...

    async def start(self, task_id: str) -> None:
        ...

    async def pause(self, task_id: str) -> None:
        ...

    async def resume(self, task_id: str) -> None:
        ...

    async def stop(self, task_id: str) -> None:
        ...

    async def remove(self, task_id: str, delete_files: bool = False) -> None:
        ...

    async def recheck(self, task_id: str) -> None:
        ...

    async def apply_options(self, task_id: str, options: EngineTorrentOptions) -> None:
        ...

    async def get_status(self, task_id: str) -> EngineTorrentStatus:
        ...

    async def get_files(self, task_id: str) -> list[EngineTorrentFile]:
        ...

    async def save_resume_data(self, task_id: str) -> bytes | None:
        ...

    async def read_stream_chunk(
        self, task_id: str, file_index: int, offset: int, length: int
    ) -> bytes:
        ...

    async def close(self) -> None:
        ...
