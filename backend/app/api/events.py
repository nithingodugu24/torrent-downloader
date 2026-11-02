from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_torrent_service
from app.db.session import get_db
from app.schemas.torrent import TaskEventRead
from app.services.torrent_service import TorrentService

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[TaskEventRead])
async def list_events(
    task_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    service: TorrentService = Depends(get_torrent_service),
) -> list[TaskEventRead]:
    events = await service.list_events(db, task_id=task_id)
    return [TaskEventRead.model_validate(event) for event in events]
