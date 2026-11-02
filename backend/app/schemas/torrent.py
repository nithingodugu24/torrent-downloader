from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TorrentStatus(StrEnum):
    queued = "queued"
    metadata = "metadata"
    downloading = "downloading"
    seeding = "seeding"
    paused = "paused"
    completed = "completed"
    errored = "errored"
    stopped = "stopped"


class MagnetCreate(BaseModel):
    magnet_uri: str = Field(min_length=8)
    save_path: str | None = None
    category: str | None = Field(default=None, max_length=100)
    priority: int = Field(default=4, ge=0, le=7)
    is_sequential: bool = False

    @field_validator("magnet_uri")
    @classmethod
    def validate_magnet(cls, value: str) -> str:
        if not value.startswith("magnet:?"):
            raise ValueError("magnet_uri must start with magnet:?")
        return value


class TorrentPatch(BaseModel):
    priority: int | None = Field(default=None, ge=0, le=7)
    save_path: str | None = None
    category: str | None = Field(default=None, max_length=100)
    download_limit: int | None = Field(default=None, ge=0)
    upload_limit: int | None = Field(default=None, ge=0)
    seed_limit: float | None = Field(default=None, ge=0)
    max_connections: int | None = Field(default=None, ge=0)
    is_sequential: bool | None = None
    queue_position: int | None = Field(default=None, ge=0)


class TorrentTaskRead(BaseModel):
    id: str
    name: str
    info_hash: str | None
    magnet_uri: str | None
    torrent_file_path: str | None
    save_path: str
    status: str
    progress: float
    download_speed: int
    upload_speed: int
    ratio: float
    total_size: int
    downloaded: int
    uploaded: int
    peers: int
    seeds: int
    priority: int
    category: str | None
    queue_position: int
    is_sequential: bool
    download_limit: int | None
    upload_limit: int | None
    seed_limit: float | None
    max_connections: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class TorrentFileRead(BaseModel):
    index: int
    path: str
    size: int
    progress: float
    priority: int
    download_url: str | None = None
    stream_url: str | None = None


class TaskEventRead(BaseModel):
    id: int
    task_id: str | None
    level: str
    event_type: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkAction(BaseModel):
    task_ids: list[str] = Field(min_length=1, max_length=200)
