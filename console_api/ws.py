"""WebSocket endpoint for live match updates."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

_active_connections: list[WebSocket] = []


@router.websocket("/live")
async def ws_live(websocket: WebSocket):
    await websocket.accept()
    _active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        if websocket in _active_connections:
            _active_connections.remove(websocket)


async def broadcast(data: dict) -> None:
    dead: list[WebSocket] = []
    payload = json.dumps(data, default=str)
    for ws in _active_connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _active_connections.remove(ws)
