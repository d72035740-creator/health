import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.simulation.engine import simulation_engine


logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/simulation")
async def simulation_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    client = websocket.client.host if websocket.client else "unknown"
    logger.info("Simulation WebSocket connected", extra={"client": client})

    try:
        while True:
            event = simulation_engine.clock_event()
            await websocket.send_json(event.model_dump(mode="json"))
            await asyncio.sleep(0.75)
    except WebSocketDisconnect:
        logger.info("Simulation WebSocket disconnected", extra={"client": client})
    except Exception:
        logger.exception("Unexpected simulation WebSocket failure", extra={"client": client})
        await websocket.close(code=1011)

