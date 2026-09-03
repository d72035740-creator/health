import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.runtime import runtime_service

router=APIRouter()
@router.websocket('/ws/runtime')
async def runtime_stream(websocket: WebSocket)->None:
    await websocket.accept(); seen=object()
    try:
        while True:
            snapshot=runtime_service.snapshot()
            cycle=snapshot.cycle_id if snapshot else None
            if cycle != seen:
                seen=cycle
                await websocket.send_json({'type':'runtime.snapshot','snapshot':snapshot.model_dump(mode='json') if snapshot else None,'status':runtime_service.status()})
            await asyncio.sleep(.5)
    except WebSocketDisconnect: return
