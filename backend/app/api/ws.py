from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps import get_broadcaster
from app.services.broadcaster import TorrentBroadcaster

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/torrents")
async def torrent_updates(
    websocket: WebSocket,
    broadcaster: TorrentBroadcaster = Depends(get_broadcaster),
) -> None:
    await broadcaster.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await broadcaster.disconnect(websocket)
