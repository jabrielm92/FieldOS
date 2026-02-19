"""
Real-time WebSocket endpoint for FieldOS live operations.

Clients connect to /api/v1/ws/{tenant_id}?token=<jwt>
and receive tenant-scoped events pushed from the server.

Event types pushed to clients:
  - job_created / job_updated / job_status_changed
  - lead_created
  - message_received
  - dispatch_update
  - tech_location_update (Phase 2)
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from jose import jwt, JWTError

from core.config import JWT_SECRET, JWT_ALGORITHM
from core.websocket import manager

router = APIRouter(tags=["realtime"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for tenant-scoped real-time events.

    Authentication: pass JWT as `?token=<jwt>` query parameter.
    The token's tenant_id must match the path tenant_id.
    """
    # Authenticate the WebSocket connection via the JWT token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        token_tenant_id = payload.get("tenant_id")
        role = payload.get("role")

        # Allow superadmin to subscribe to any tenant
        if role != "SUPERADMIN" and token_tenant_id != tenant_id:
            await websocket.close(code=4003, reason="Tenant mismatch")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, tenant_id)
    logger.info(f"WS client connected: tenant={tenant_id}")

    try:
        while True:
            # Keep connection alive; clients can send ping messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
        logger.info(f"WS client disconnected: tenant={tenant_id}")
