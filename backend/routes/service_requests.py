"""Service Requests routes - manage customer portal service requests"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs, calculate_quote_amount
from models import (
    Quote, QuoteStatus,
    Job, JobType, JobStatus, JobCreatedBy,
    LeadStatus,
)

router = APIRouter(prefix="/service-requests", tags=["service_requests"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_service_requests(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List service requests from customer portal"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status

    requests = await db.service_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)

    # Enrich with customer info
    for req in requests:
        customer = await db.customers.find_one(
            {"id": req.get("customer_id")},
            {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1}
        )
        req["customer"] = serialize_doc(customer) if customer else None

    return serialize_docs(requests)


@router.post("/{request_id}/convert")
async def convert_service_request_to_job(
    request_id: str,
    job_type: str = "DIAGNOSTIC",
    scheduled_date: Optional[str] = None,
    scheduled_time_slot: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Convert a service request to a booked job"""
    import pytz

    service_request = await db.service_requests.find_one(
        {"id": request_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not service_request:
        raise HTTPException(status_code=404, detail="Service request not found")

    # Get customer
    customer = await db.customers.find_one({"id": service_request["customer_id"]}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get or use property
    property_id = service_request.get("property_id")
    if not property_id:
        prop = await db.properties.find_one({"customer_id": customer["id"]}, {"_id": 0})
        if prop:
            property_id = prop["id"]

    if not property_id:
        raise HTTPException(status_code=400, detail="No property found for customer")

    # Get tenant for timezone
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz = pytz.timezone(tenant.get("timezone", "America/New_York"))

    # Determine schedule
    date_to_use = scheduled_date or service_request.get("preferred_date") or (datetime.now(tenant_tz) + timedelta(days=1)).strftime("%Y-%m-%d")
    time_slot = scheduled_time_slot or service_request.get("preferred_time_slot") or "morning"

    # Create time window based on slot
    from datetime import datetime as dt
    base_date = dt.strptime(date_to_use, "%Y-%m-%d")

    slot_times = {
        "morning": ("08:00", "12:00"),
        "afternoon": ("12:00", "16:00"),
        "evening": ("16:00", "19:00")
    }
    start_time, end_time = slot_times.get(time_slot, ("08:00", "12:00"))

    service_window_start = tenant_tz.localize(dt.strptime(f"{date_to_use} {start_time}", "%Y-%m-%d %H:%M"))
    service_window_end = tenant_tz.localize(dt.strptime(f"{date_to_use} {end_time}", "%Y-%m-%d %H:%M"))

    # Calculate quote amount
    urgency = service_request.get("urgency", "ROUTINE")
    quote_amount = calculate_quote_amount(job_type, urgency)

    # Find or create lead
    lead = await db.leads.find_one({
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "tags": "portal_request"
    }, {"_id": 0})

    lead_id = lead["id"] if lead else None

    # Create job
    job = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "lead_id": lead_id,
        "job_type": job_type,
        "priority": "EMERGENCY" if urgency == "EMERGENCY" else ("HIGH" if urgency == "URGENT" else "NORMAL"),
        "service_window_start": service_window_start.isoformat(),
        "service_window_end": service_window_end.isoformat(),
        "status": "BOOKED",
        "created_by": "STAFF",
        "notes": service_request.get("issue_description"),
        "quote_amount": quote_amount,
        "reminder_day_before_sent": False,
        "reminder_morning_of_sent": False,
        "en_route_sms_sent": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.jobs.insert_one(job)

    # Update service request status
    await db.service_requests.update_one(
        {"id": request_id},
        {"$set": {"status": "CONVERTED_TO_LEAD", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    # Update lead status if exists
    if lead_id:
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {"status": LeadStatus.JOB_BOOKED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    # Create quote
    quote = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "job_id": job["id"],
        "amount": quote_amount,
        "currency": "USD",
        "description": f"{job_type} service - {service_request.get('issue_description', '')[:100]}",
        "status": "SENT",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.quotes.insert_one(quote)

    # Update job with quote_id
    await db.jobs.update_one({"id": job["id"]}, {"$set": {"quote_id": quote["id"]}})

    # Send confirmation SMS
    from services.twilio_service import twilio_service

    msg = f"Hi {customer['first_name']}! Your service appointment is confirmed for {base_date.strftime('%A, %B %d')} ({time_slot}). Quote: ${quote_amount:.2f}."
    if tenant.get("sms_signature"):
        msg += f" {tenant['sms_signature']}"

    await twilio_service.send_sms(to_phone=customer["phone"], body=msg)

    return {
        "success": True,
        "job": serialize_doc(job),
        "quote": serialize_doc(quote)
    }
