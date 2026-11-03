"""In-process pub/sub that pushes events to WebSocket clients.

Clients subscribe to topics ("projects", "runs:42"...). `publish` can be called
from async code; `publish_threadsafe` from sync endpoints and worker threads.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class RealtimeHub:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, ws: WebSocket, topics: list[str]) -> None:
        for topic in topics:
            self._subscribers[topic].add(ws)

    def unsubscribe(self, ws: WebSocket) -> None:
        for sockets in self._subscribers.values():
            sockets.discard(ws)

    async def publish(self, topic: str, event_type: str, data: dict[str, Any]) -> None:
        message = {
            "topic": topic,
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        for ws in list(self._subscribers.get(topic, ())):
            try:
                await ws.send_json(message)
            except Exception:  # client went away mid-send
                logger.debug("Dropping dead websocket on topic %s", topic)
                self.unsubscribe(ws)

    def publish_threadsafe(self, topic: str, event_type: str, data: dict[str, Any]) -> None:
        if self._loop is None:
            logger.warning("Realtime hub not bound to a loop; event %s dropped", event_type)
            return
        asyncio.run_coroutine_threadsafe(self.publish(topic, event_type, data), self._loop)


hub = RealtimeHub()
