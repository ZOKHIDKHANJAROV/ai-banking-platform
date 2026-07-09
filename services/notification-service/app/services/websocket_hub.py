import asyncio
import uuid

from fastapi import WebSocket
from fastapi import WebSocketDisconnect


class WebSocketHub:
    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    async def connect(
        self,
        websocket: WebSocket
    ) -> None:
        await websocket.accept()

        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(
        self,
        websocket: WebSocket
    ) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(
        self,
        payload: dict
    ) -> str:
        message_id = f"ws-{uuid.uuid4()}"

        async with self._lock:
            connections = list(self._connections)

        stale_connections = []

        for websocket in connections:
            try:
                await websocket.send_json(
                    {
                        "id": message_id,
                        "type": "fraud-alert",
                        "payload": payload
                    }
                )
            except RuntimeError:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            await self.disconnect(websocket)

        return message_id

    async def serve(
        self,
        websocket: WebSocket
    ) -> None:
        await self.connect(websocket)

        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await self.disconnect(websocket)
