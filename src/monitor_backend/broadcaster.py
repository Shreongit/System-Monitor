import asyncio
from typing import Set
from fastapi import WebSocket


class Broadcaster:
    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._clients:
                self._clients.remove(ws)

    async def broadcast(self, payload):
        # send payload to all connected clients; remove closed websockets
        to_remove = []
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                to_remove.append(ws)
        if to_remove:
            async with self._lock:
                for w in to_remove:
                    if w in self._clients:
                        self._clients.remove(w)