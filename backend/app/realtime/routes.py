import re
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.realtime.hub import hub
from app.services.auth import SESSION_COOKIE, AuthService

router = APIRouter()

TOPIC_PATTERN = re.compile(r"^(projects|agents|approvals|settings|events|runs:\d+)$")


def get_session_factory() -> Callable[[], Session]:
    """Short-lived sessions: a long-lived socket must not hold a pooled DB connection."""
    return SessionLocal


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    sessions: Annotated[Callable[[], Session], Depends(get_session_factory)],
    topics: str = Query(..., description="Comma-separated topics"),
):
    # Browsers send same-origin cookies on the WebSocket handshake
    with sessions() as db:
        authenticated = AuthService(db).user_for_token(ws.cookies.get(SESSION_COOKIE)) is not None
    if not authenticated:
        await ws.close(code=1008, reason="Unauthorized")
        return
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
