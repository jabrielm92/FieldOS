"""Leads routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs
from models import Lead, LeadCreate

router = APIRouter(prefix="/leads", tags=["leads"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    urgency: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List leads with optional filters"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    if source:
        query["source"] = source
    if urgency:
        query["urgency"] = urgency

    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    # Enrich leads with customer and property data
    enriched_leads = []
    for lead in leads:
        customer = None
        prop = None
        if lead.get("customer_id"):
            customer = await db.customers.find_one({"id": lead["customer_id"]}, {"_id": 0})
        if lead.get("property_id"):
            prop = await db.properties.find_one({"id": lead["property_id"]}, {"_id": 0})

        # Also get address from lead itself if stored there
        address = lead.get("captured_address") or lead.get("address_line1") or (prop.get("address_line1") if prop else None)

        enriched_leads.append({
            **serialize_doc(lead),
            "customer": serialize_doc(customer) if customer else None,
            "property": serialize_doc(prop) if prop else None,
            "address": address,
            "caller_name": lead.get("caller_name") or (f"{customer['first_name']} {customer['last_name']}" if customer else "Unknown")
        })

    return enriched_leads


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get lead with customer and conversation"""
    lead = await db.leads.find_one(
        {"id": lead_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get customer if linked
    customer = None
    if lead.get("customer_id"):
        customer = await db.customers.find_one(
            {"id": lead["customer_id"]}, {"_id": 0}
        )

    # Get conversation
    conversation = await db.conversations.find_one(
        {"lead_id": lead_id}, {"_id": 0}
    )

    messages = []
    if conversation:
        messages = await db.messages.find(
            {"conversation_id": conversation["id"]}, {"_id": 0}
        ).sort("created_at", 1).to_list(100)

    return {
        **serialize_doc(lead),
        "customer": serialize_doc(customer) if customer else None,
        "conversation": serialize_doc(conversation) if conversation else None,
        "messages": serialize_docs(messages)
    }


@router.post("")
async def create_lead(
    data: LeadCreate,
    tenant_id: Optional[str] = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new lead"""
    # For superadmin without tenant_id, require it to be specified
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for lead creation")

    lead = Lead(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )

    lead_dict = lead.model_dump(mode='json')
    await db.leads.insert_one(lead_dict)

    return serialize_doc(lead_dict)


@router.put("/{lead_id}")
async def update_lead(
    lead_id: str,
    data: LeadCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update lead"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["last_activity_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.leads.update_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return serialize_doc(lead)


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a lead"""
    result = await db.leads.delete_one({"id": lead_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "message": "Lead deleted"}


@router.post("/bulk-delete")
async def bulk_delete_leads(
    lead_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete leads and their associated jobs"""
    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided")

    # Delete associated jobs first
    await db.jobs.delete_many({"lead_id": {"$in": lead_ids}, "tenant_id": tenant_id})

    # Delete the leads
    result = await db.leads.delete_many({"id": {"$in": lead_ids}, "tenant_id": tenant_id})

    return {"success": True, "deleted_count": result.deleted_count}
