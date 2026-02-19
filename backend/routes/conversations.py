"""Conversations and Messages routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs
from models import (
    Message, MessageCreate, MessageDirection, SenderType, PreferredChannel,
)

router = APIRouter(tags=["conversations"])
logger = logging.getLogger(__name__)


@router.get("/conversations")
async def list_conversations(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List conversations"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status

    conversations = await db.conversations.find(query, {"_id": 0}).sort("last_message_at", -1).to_list(100)

    for conv in conversations:
        customer = await db.customers.find_one({"id": conv.get("customer_id")}, {"_id": 0})
        conv["customer"] = serialize_doc(customer) if customer else None

    return serialize_docs(conversations)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get conversation with messages"""
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await db.messages.find(
        {"conversation_id": conversation_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)

    customer = await db.customers.find_one({"id": conv.get("customer_id")}, {"_id": 0})

    return {
        **serialize_doc(conv),
        "customer": serialize_doc(customer) if customer else None,
        "messages": serialize_docs(messages)
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get messages for a conversation"""
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await db.messages.find(
        {"conversation_id": conversation_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)

    return serialize_docs(messages)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation and all its messages"""
    # Delete messages first
    await db.messages.delete_many({"conversation_id": conversation_id, "tenant_id": tenant_id})
    # Delete conversation
    result = await db.conversations.delete_one({"id": conversation_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "message": "Conversation deleted"}


@router.post("/conversations/bulk-delete")
async def bulk_delete_conversations(
    conversation_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete conversations and their messages"""
    if not conversation_ids:
        raise HTTPException(status_code=400, detail="No conversation IDs provided")

    # Delete messages
    await db.messages.delete_many({"conversation_id": {"$in": conversation_ids}, "tenant_id": tenant_id})
    # Delete conversations
    result = await db.conversations.delete_many({"id": {"$in": conversation_ids}, "tenant_id": tenant_id})
    return {"success": True, "deleted_count": result.deleted_count}


@router.post("/messages")
async def send_message(
    data: MessageCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send a message (staff sending from UI)"""
    # Verify conversation exists
    conv = await db.conversations.find_one(
        {"id": data.conversation_id, "tenant_id": tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get customer and tenant
    customer = await db.customers.find_one({"id": data.customer_id}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})

    # Send SMS via Twilio if channel is SMS
    twilio_result = None
    if data.channel == PreferredChannel.SMS and customer and tenant and tenant.get("twilio_phone_number"):
        from services.twilio_service import twilio_service

        twilio_result = await twilio_service.send_sms(
            to_phone=customer["phone"],
            body=data.content,
            from_phone=tenant["twilio_phone_number"]
        )

    # Create message record
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=data.conversation_id,
        customer_id=data.customer_id,
        lead_id=data.lead_id,
        direction=MessageDirection.OUTBOUND,
        sender_type=SenderType.STAFF,
        channel=data.channel,
        content=data.content,
        metadata={"twilio_sid": twilio_result.get("provider_message_id") if twilio_result else None}
    )

    msg_dict = msg.model_dump(mode='json')
    await db.messages.insert_one(msg_dict)

    # Update conversation
    await db.conversations.update_one(
        {"id": data.conversation_id},
        {"$set": {
            "last_message_from": SenderType.STAFF.value,
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return serialize_doc(msg_dict)
