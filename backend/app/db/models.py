from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TorrentTask(Base):
    __tablename__ = "torrent_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(500), default="")
    info_hash: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    magnet_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    torrent_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    save_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True, default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    download_speed: Mapped[int] = mapped_column(Integer, default=0)
    upload_speed: Mapped[int] = mapped_column(Integer, default=0)
    ratio: Mapped[float] = mapped_column(Float, default=0.0)
    total_size: Mapped[int] = mapped_column(Integer, default=0)
    downloaded: Mapped[int] = mapped_column(Integer, default=0)
    uploaded: Mapped[int] = mapped_column(Integer, default=0)
    peers: Mapped[int] = mapped_column(Integer, default=0)
    seeds: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=4)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    queue_position: Mapped[int] = mapped_column(Integer, default=0)
    is_sequential: Mapped[bool] = mapped_column(Boolean, default=False)
    download_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_connections: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list[TaskEvent]] = relationship(
        "TaskEvent", back_populates="task", cascade="all, delete-orphan"
    )


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("torrent_tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    level: Mapped[str] = mapped_column(String(20), default="info")
    event_type: Mapped[str] = mapped_column(String(50), default="event")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[TorrentTask | None] = relationship("TorrentTask", back_populates="events")
