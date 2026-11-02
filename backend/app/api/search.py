import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import search as service
from app.services.search import Provider

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query(min_length=1, max_length=200),
    provider: list[Provider] = Query(default=list(service.BASES)),
    page: int = Query(default=1, ge=1, le=100),
):
    if not q.strip():
        raise HTTPException(422, "Enter a search term.")
    return await service.search(q.strip(), provider, page)


class ResolveRequest(BaseModel):
    provider: Provider
    url: str = Field(max_length=2048)


@router.post("/resolve")
async def resolve(payload: ResolveRequest):
    try:
        return {"magnet_uri": await service.resolve_magnet(payload.provider, payload.url)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except (httpx.HTTPError, TimeoutError) as exc:
        raise HTTPException(502, "Could not reach the source page. Try again later.") from exc
