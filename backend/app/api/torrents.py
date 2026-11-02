from __future__ import annotations

import asyncio
import logging
import mimetypes
from dataclasses import asdict
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_torrent_service
from app.db.session import get_db
from app.schemas.torrent import MagnetCreate, TorrentFileRead, TorrentPatch, TorrentTaskRead
from app.services.torrent_service import TorrentService
from app.utils.paths import safe_resolve_under_root
from app.utils.streaming import VIDEO_EXTENSIONS, byte_range

router = APIRouter(prefix="/api/torrents", tags=["torrents"])
logger = logging.getLogger(__name__)


@router.post("/magnet", response_model=TorrentTaskRead, status_code=201)
async def add_magnet(
    payload: MagnetCreate,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    task = await service.add_magnet(
        db,
        payload.magnet_uri,
        payload.save_path,
        payload.category,
        payload.priority,
        payload.is_sequential,
    )
    return TorrentTaskRead.model_validate(task)


@router.post("/file", response_model=TorrentTaskRead, status_code=201)
async def add_torrent_file(
    file: UploadFile = File(...),
    save_path: str | None = Form(default=None),
    category: str | None = Form(default=None),
    priority: int = Form(default=4),
    is_sequential: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    content = await file.read(service.settings.max_upload_size_mb * 1024 * 1024 + 1)
    task = await service.add_torrent_file(
        db,
        file.filename or "upload.torrent",
        content,
        save_path,
        category,
        priority,
        is_sequential,
    )
    return TorrentTaskRead.model_validate(task)


@router.get("", response_model=list[TorrentTaskRead])
async def list_torrents(
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> list[TorrentTaskRead]:
    tasks = await service.list_tasks(db, status, search, sort, order)
    return [TorrentTaskRead.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TorrentTaskRead)
async def get_torrent(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    task = await service.get_task(db, task_id)
    return TorrentTaskRead.model_validate(task)


@router.patch("/{task_id}", response_model=TorrentTaskRead)
async def update_torrent(
    task_id: str,
    payload: TorrentPatch,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    task = await service.update_task(db, task_id, payload)
    return TorrentTaskRead.model_validate(task)


@router.post("/{task_id}/start", response_model=TorrentTaskRead)
async def start_torrent(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    task = await service.action(db, task_id, "start")
    return TorrentTaskRead.model_validate(task)


@router.post("/{task_id}/pause", response_model=TorrentTaskRead)
async def pause_torrent(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    task = await service.action(db, task_id, "pause")
    return TorrentTaskRead.model_validate(task)


@router.post("/{task_id}/resume", response_model=TorrentTaskRead)
async def resume_torrent(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    task = await service.action(db, task_id, "resume")
    return TorrentTaskRead.model_validate(task)


@router.post("/{task_id}/stop", response_model=TorrentTaskRead)
async def stop_torrent(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    task = await service.action(db, task_id, "stop")
    return TorrentTaskRead.model_validate(task)


@router.post("/{task_id}/remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_torrent(
    task_id: str,
    delete_files: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> Response:
    await service.action(db, task_id, "remove", delete_files=delete_files)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{task_id}/recheck", response_model=TorrentTaskRead)
async def recheck_torrent(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> TorrentTaskRead:
    task = await service.action(db, task_id, "recheck")
    return TorrentTaskRead.model_validate(task)


@router.get("/{task_id}/files", response_model=list[TorrentFileRead])
async def list_files(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> list[TorrentFileRead]:
    task = await service.get_task(db, task_id)
    files = await service.get_files(db, task_id)
    result: list[TorrentFileRead] = []
    for item in files:
        file_path = safe_resolve_under_root(Path(task.save_path), item.path)
        download_url = (
            f"/api/torrents/{task_id}/files/{item.index}/download"
            if task.status in {"completed", "seeding"} and file_path.is_file()
            else None
        )
        stream_url = (
            f"/api/torrents/{task_id}/files/{item.index}/stream"
            if Path(item.path).suffix.lower() in VIDEO_EXTENSIONS and item.size > 0 else None
        )
        result.append(
            TorrentFileRead(**asdict(item), download_url=download_url, stream_url=stream_url)
        )
    return result


@router.get("/{task_id}/files/{file_index}/download")
async def download_file(
    task_id: str,
    file_index: int,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> FileResponse:
    task = await service.get_task(db, task_id)
    if task.status not in {"completed", "seeding"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Files are available for browser download after the torrent completes.",
        )
    files = await service.get_files(db, task_id)
    match = next((item for item in files if item.index == file_index), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    file_path = safe_resolve_under_root(Path(task.save_path), match.path)
    return FileResponse(file_path, filename=Path(match.path).name)


@router.post("/{task_id}/files/{file_index}/stream")
async def prepare_stream(
    task_id: str,
    file_index: int,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> Response:
    task = await service.get_task(db, task_id)
    # Restore a stopped task before asking the engine for metadata.
    if task.status in {"stopped", "paused", "errored"}:
        task = await service.action(db, task_id, "resume")
    files = await service.get_files(db, task_id)
    match = next((item for item in files if item.index == file_index), None)
    if not match:
        raise HTTPException(404, "Video file not found. Wait for torrent metadata.")
    if Path(match.path).suffix.lower() not in VIDEO_EXTENSIONS or match.size <= 0:
        raise HTTPException(400, "Select a video file to stream.")
    await service.update_task(
        db, task_id, TorrentPatch(is_sequential=True, priority=max(1, task.priority))
    )
    # Do not advertise a playable URL until an initial video buffer is downloaded.
    async def buffer_start() -> None:
        offset = 0
        target = min(match.size, 4 * 1024 * 1024)
        while offset < target:
            chunk = await service.engine.read_stream_chunk(
                task_id, file_index, offset, min(256 * 1024, target - offset)
            )
            if not chunk:
                raise RuntimeError("Video data is unavailable.")
            offset += len(chunk)

    from fastapi.responses import JSONResponse

    try:
        async with asyncio.timeout(10):
            await buffer_start()
    except TimeoutError:
        return JSONResponse({"ready": False}, status_code=202)
    except (RuntimeError, KeyError, OSError) as exc:
        logger.warning("Video preparation failed: %s", exc, exc_info=True)
        raise HTTPException(409, "Video is unavailable. Resume the torrent and retry.") from exc
    return JSONResponse({
        "url": f"/api/torrents/{task_id}/files/{file_index}/stream", "ready": True,
    })


@router.api_route("/{task_id}/files/{file_index}/stream", methods=["GET", "HEAD"])
async def stream_file(
    task_id: str,
    file_index: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> Response:
    task = await service.get_task(db, task_id)
    if task.status in {"paused", "stopped", "errored"}:
        raise HTTPException(409, "Resume the torrent before streaming.")
    files = await service.get_files(db, task_id)
    match = next((item for item in files if item.index == file_index), None)
    if not match:
        raise HTTPException(404, "Video file not found. Wait for torrent metadata.")
    if Path(match.path).suffix.lower() not in VIDEO_EXTENSIONS:
        raise HTTPException(400, "Select a video file to stream.")
    safe_resolve_under_root(Path(task.save_path), match.path)
    start, end = byte_range(request.headers.get("range"), match.size)
    headers = {
        "Accept-Ranges": "bytes", "Content-Length": str(end - start + 1),
        "Cache-Control": "no-store", "X-Accel-Buffering": "no",
    }
    code = 206 if "range" in request.headers else 200
    if code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{match.size}"
    media_type = mimetypes.guess_type(match.path)[0] or "application/octet-stream"
    if request.method == "HEAD":
        return Response(status_code=code, headers=headers, media_type=media_type)

    async def read(offset: int) -> bytes:
        return await service.engine.read_stream_chunk(
            task_id, file_index, offset, min(256 * 1024, end - offset + 1)
        )

    # Buffer the first chunk before sending headers so failures have a useful HTTP status.
    try:
        async with asyncio.timeout(15):
            first = await read(start)
    except (TimeoutError, RuntimeError, KeyError, OSError) as exc:
        logger.warning("Stream startup failed for %s file %s: %s", task_id, file_index, exc,
                       exc_info=True)
        raise HTTPException(
            503, "Video is buffering or unavailable. Check seeds and retry.",
            headers={"Retry-After": "5"},
        ) from exc

    async def content():
        yield first
        offset = start + len(first)
        while offset <= end:
            if await request.is_disconnected():
                return
            chunk = await read(offset)
            if not chunk:
                raise RuntimeError("Video stream ended before the requested range completed.")
            yield chunk
            offset += len(chunk)

    return StreamingResponse(content(), status_code=code, headers=headers, media_type=media_type)
