import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Settings(BaseModel):
    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./state/uwsleech.db"
    storage_root: Path = Path("./downloads")
    torrent_state_dir: Path = Path("./state/resume")
    torrent_file_dir: Path = Path("./torrent-files")
    allowed_hosts: list[str] = Field(default_factory=lambda: ["127.0.0.1", "localhost"])
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )
    max_upload_size_mb: int = 5
    global_download_limit: int = 0
    global_upload_limit: int = 0
    max_active_downloads: int = 4
    max_active_seeds: int = 4
    websocket_interval_seconds: float = 1.0
    public_rate_limit_per_minute: int = 0

    model_config = ConfigDict(extra="ignore")

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def ensure_directories(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.torrent_state_dir.mkdir(parents=True, exist_ok=True)
        self.torrent_file_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, env_file: Path = Path(".env")) -> "Settings":
        raw = _read_env_file(env_file)
        raw.update(os.environ)
        values: dict[str, Any] = {}
        for field_name in cls.model_fields:
            env_name = field_name.upper()
            if env_name in raw:
                values[field_name] = raw[env_name]
        return cls(**values)


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
