"""
WebSocket Connection Manager for FieldOS Real-Time Events.

Supports tenant-scoped broadcasting so each tenant only receives their own events.
Usage:
    manager = ConnectionManager()

    # In a WebSocket endpoint:
    await manager.connect(websocket, tenant_id)

    # From any route or service to push live updates:
    await manager.broadcast_to_tenant(tenant_id, {"type": "job_updated", "data": job})
"""
import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Maps tenant_id -> list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str) -> None:
        await websocket.accept()
        if tenant_id not in self._connections:
            self._connections[tenant_id] = []
        self._connections[tenant_id].append(websocket)
        logger.info(f"WS connected: tenant={tenant_id} total={len(self._connections[tenant_id])}")

    def disconnect(self, websocket: WebSocket, tenant_id: str) -> None:
        if tenant_id in self._connections:
            try:
                self._connections[tenant_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[tenant_id]:
                del self._connections[tenant_id]
        logger.info(f"WS disconnected: tenant={tenant_id}")

    async def broadcast_to_tenant(self, tenant_id: str, payload: dict) -> None:
        """Send a JSON event to all WebSocket clients for a given tenant."""
        connections = self._connections.get(tenant_id, [])
        dead: List[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, tenant_id)

    async def broadcast_to_all(self, payload: dict) -> None:
        """Send a JSON event to every connected client (superadmin use-cases)."""
        for tenant_id in list(self._connections.keys()):
            await self.broadcast_to_tenant(tenant_id, payload)

    def active_tenant_count(self) -> int:
        return len(self._connections)

    def active_connection_count(self) -> int:
        return sum(len(v) for v in self._connections.values())


# Singleton instance – import this everywhere
manager = ConnectionManager()
