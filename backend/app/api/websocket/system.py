import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.domain.enums import SubsystemStatus
from app.domain.models import SystemHeartbeat


logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/system")
async def system_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    client = websocket.client.host if websocket.client else "unknown"
    logger.info("WebSocket connected", extra={"client": client})

    try:
        while True:
            heartbeat = SystemHeartbeat(
                timestamp=datetime.now(timezone.utc),
                backend_status=SubsystemStatus.READY,
            )
            await websocket.send_json(heartbeat.model_dump(mode="json"))
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", extra={"client": client})
    except Exception:
        logger.exception("Unexpected WebSocket failure", extra={"client": client})
        await websocket.close(code=1011)

