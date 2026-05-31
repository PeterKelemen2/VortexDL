"""In-process Server-Sent Events bus for pushing job updates to clients.

Each connected browser subscribes with its authenticated ``user_id`` and
receives an :class:`asyncio.Queue` of JSON-encoded events. The job queue calls
:meth:`SSEBus.emit` after every status transition so the frontend reflects
progress in real time without polling.

This is process-local (matching the in-process job queue). For a multi-process
deployment, back this with Redis pub/sub while keeping the same interface.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger("app.sse_bus")


class SSEBus:
    def __init__(self) -> None:
        self._listeners: dict[int, set[asyncio.Queue[str]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: int) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._listeners.setdefault(user_id, set()).add(queue)
        return queue

    async def unsubscribe(self, user_id: int, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            listeners = self._listeners.get(user_id)
            if listeners is not None:
                listeners.discard(queue)
                if not listeners:
                    self._listeners.pop(user_id, None)

    def emit(self, user_id: int, event_type: str, data: dict[str, Any]) -> None:
        """Fan out an event to all of a user's listeners (non-blocking)."""
        listeners = self._listeners.get(user_id)
        if not listeners:
            return
        payload = json.dumps({"type": event_type, "data": data}, default=str)
        for queue in list(listeners):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:  # slow consumer: drop oldest semantics
                logger.debug("SSE queue full for user %s; dropping event", user_id)


# Module singleton used by the application.
sse_bus = SSEBus()
