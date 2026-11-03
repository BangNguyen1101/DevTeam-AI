import re

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.realtime.hub import hub

router = APIRouter()

TOPIC_PATTERN = re.compile(r"^(projects|agents|approvals|settings|events|runs:\d+)$")


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, topics: str = Query(..., description="Comma-separated topics")):
    requested = [t.strip() for t in topics.split(",") if t.strip()]
    invalid = [t for t in requested if not TOPIC_PATTERN.match(t)]
    if not requested or invalid:
        await ws.close(code=1008, reason=f"Invalid topics: {invalid or 'none'}")
        return

    await ws.accept()
    hub.subscribe(ws, requested)
    await ws.send_json({"type": "subscribed", "topics": requested})
    try:
        while True:
            # Clients may send "ping" to keep the connection alive
            if await ws.receive_text() == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(ws)
