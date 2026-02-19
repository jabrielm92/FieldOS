"""Customer Portal routes - public endpoints for customer self-service"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4
import logging
import os

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs, normalize_phone_e164

router = APIRouter(prefix="/portal", tags=["portal"])
logger = logging.getLogger(__name__)


# ============= PORTAL TOKEN GENERATION =============

async def generate_portal_token(customer_id: str, tenant_id: str) -> str:
    """Generate a portal access token for a customer"""
    import secrets

    random_part = secrets.token_urlsafe(16)
    token = f"{customer_id[:8]}-{random_part}"

    await db.customers.update_one(
        {"id": customer_id, "tenant_id": tenant_id},
        {"$set": {"portal_token": token, "portal_token_created": datetime.now(timezone.utc).isoformat()}}
    )

    return token


@router.post("/generate-link")
async def generate_portal_link(
    customer_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Generate a customer portal link"""
    customer = await db.customers.find_one({"id": customer_id, "tenant_id": tenant_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    token = await generate_portal_token(customer_id, tenant_id)
    base_url = os.environ.get('APP_BASE_URL', 'http://localhost:3000')
    portal_url = f"{base_url}/portal/{token}"

    return {
        "success": True,
        "portal_url": portal_url,
        "token": token
    }


# ============= PUBLIC PORTAL ENDPOINTS (no auth required) =============

@router.get("/{token}")
async def get_portal_data(token: str):
    """Get customer portal data (public endpoint)"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    tenant_id = customer["tenant_id"]
    customer_id = customer["id"]

    # Get tenant info
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "name": 1, "primary_phone": 1})

    # Get upcoming jobs
    now = datetime.now(timezone.utc)
    upcoming_jobs = await db.jobs.find({
        "customer_id": customer_id,
        "status": {"$in": ["BOOKED", "EN_ROUTE"]},
        "service_window_start": {"$gte": now.isoformat()}
    }, {"_id": 0}).sort("service_window_start", 1).to_list(10)

    # Enrich with property info
    for job in upcoming_jobs:
        prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
        job["property"] = serialize_doc(prop) if prop else None
        if job.get("assigned_technician_id"):
            tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0, "name": 1, "phone": 1})
            job["technician"] = serialize_doc(tech) if tech else None

    # Get past jobs
    past_jobs = await db.jobs.find({
        "customer_id": customer_id,
        "status": "COMPLETED"
    }, {"_id": 0}).sort("service_window_start", -1).limit(5).to_list(5)

    # Get pending quotes
    pending_quotes = await db.quotes.find({
        "customer_id": customer_id,
        "status": {"$in": ["DRAFT", "SENT"]}
    }, {"_id": 0}).to_list(10)

    for quote in pending_quotes:
        prop = await db.properties.find_one({"id": quote.get("property_id")}, {"_id": 0})
        quote["property"] = serialize_doc(prop) if prop else None

    # Get properties
    properties = await db.properties.find({"customer_id": customer_id}, {"_id": 0}).to_list(20)

    # Get pending invoices (unpaid)
    pending_invoices = await db.invoices.find({
        "customer_id": customer_id,
        "status": {"$in": ["DRAFT", "SENT", "PARTIALLY_PAID", "OVERDUE"]}
    }, {"_id": 0}).to_list(10)

    for invoice in pending_invoices:
        job = await db.jobs.find_one({"id": invoice.get("job_id")}, {"_id": 0, "job_type": 1, "service_window_start": 1})
        invoice["job"] = serialize_doc(job) if job else None

    # Get reviews by customer
    reviews = await db.reviews.find({"customer_id": customer_id}, {"_id": 0}).to_list(20)

    # Enrich past jobs with review status
    for job in past_jobs:
        existing_review = await db.reviews.find_one({"job_id": job["id"]}, {"_id": 0})
        job["review"] = serialize_doc(existing_review) if existing_review else None

    return {
        "customer": {
            "first_name": customer.get("first_name"),
            "last_name": customer.get("last_name"),
            "phone": customer.get("phone"),
            "email": customer.get("email")
        },
        "company": serialize_doc(tenant) if tenant else None,
        "upcoming_appointments": serialize_docs(upcoming_jobs),
        "past_appointments": serialize_docs(past_jobs),
        "pending_quotes": serialize_docs(pending_quotes),
        "pending_invoices": serialize_docs(pending_invoices),
        "properties": serialize_docs(properties),
        "reviews": serialize_docs(reviews)
    }


@router.get("/{token}/branding")
async def get_portal_branding(token: str):
    """Get branding for customer portal (public endpoint)"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    tenant = await db.tenants.find_one({"id": customer["tenant_id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    branding = tenant.get("branding", {})
    defaults = {
        "logo_url": None,
        "company_name": tenant.get("name"),
        "primary_color": "#0066CC",
        "secondary_color": "#004499",
        "accent_color": "#FF6600",
        "text_on_primary": "#FFFFFF",
        "portal_title": f"{tenant.get('name')} Customer Portal",
        "portal_welcome_message": "Welcome to your customer portal",
        "portal_support_email": tenant.get("primary_contact_email"),
        "portal_support_phone": tenant.get("primary_phone"),
        "white_label_enabled": False
    }

    result = {**defaults}
    for key in defaults:
        if key in branding and branding[key]:
            result[key] = branding[key]

    return result


@router.get("/{token}/messages")
async def get_portal_messages(token: str, limit: int = 50):
    """Get conversation messages for customer portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    conversation = await db.conversations.find_one(
        {"customer_id": customer["id"]},
        {"_id": 0}
    )

    if not conversation:
        return {"conversation": None, "messages": []}

    messages = await db.messages.find(
        {"conversation_id": conversation["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    messages.reverse()

    return {
        "conversation": serialize_doc(conversation),
        "messages": serialize_docs(messages)
    }


@router.get("/{token}/invoices")
async def get_portal_invoices(token: str, status: Optional[str] = None):
    """Get all invoices for customer portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    query = {"customer_id": customer["id"]}
    if status:
        query["status"] = status

    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)

    for invoice in invoices:
        if invoice.get("job_id"):
            job = await db.jobs.find_one({"id": invoice["job_id"]}, {"_id": 0, "job_type": 1, "service_window_start": 1})
            invoice["job"] = serialize_doc(job) if job else None
        if invoice.get("property_id"):
            prop = await db.properties.find_one({"id": invoice["property_id"]}, {"_id": 0})
            invoice["property"] = serialize_doc(prop) if prop else None

    return {"invoices": serialize_docs(invoices)}


@router.get("/{token}/service-history")
async def get_portal_service_history(token: str, limit: int = 20):
    """Get full service history for customer portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    jobs = await db.jobs.find(
        {"customer_id": customer["id"]},
        {"_id": 0}
    ).sort("service_window_start", -1).limit(limit).to_list(limit)

    for job in jobs:
        if job.get("property_id"):
            prop = await db.properties.find_one({"id": job["property_id"]}, {"_id": 0})
            job["property"] = serialize_doc(prop) if prop else None
        if job.get("assigned_technician_id"):
            tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0, "name": 1})
            job["technician"] = serialize_doc(tech) if tech else None
        review = await db.reviews.find_one({"job_id": job["id"]}, {"_id": 0})
        job["review"] = serialize_doc(review) if review else None
        invoice = await db.invoices.find_one({"job_id": job["id"]}, {"_id": 0, "id": 1, "amount": 1, "status": 1})
        job["invoice"] = serialize_doc(invoice) if invoice else None

    return {"service_history": serialize_docs(jobs)}


@router.post("/{token}/quote/{quote_id}/respond")
async def respond_to_quote(token: str, quote_id: str, action: str):
    """Customer responds to a quote (accept/decline)"""
    customer = await db.customers.find_one({"portal_token": token})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    quote = await db.quotes.find_one({"id": quote_id, "customer_id": customer["id"]})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    if action == "accept":
        new_status = "ACCEPTED"
        update_field = "accepted_at"
    elif action == "decline":
        new_status = "DECLINED"
        update_field = "declined_at"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    await db.quotes.update_one(
        {"id": quote_id},
        {"$set": {
            "status": new_status,
            update_field: datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return {"success": True, "status": new_status}


@router.post("/{token}/reschedule-request")
async def request_reschedule(token: str, job_id: str, message: str):
    """Customer requests to reschedule an appointment"""
    customer = await db.customers.find_one({"portal_token": token})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    job = await db.jobs.find_one({"id": job_id, "customer_id": customer["id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tenant_id = customer["tenant_id"]

    conv = await db.conversations.find_one({
        "customer_id": customer["id"],
        "tenant_id": tenant_id,
        "status": "OPEN"
    })

    if not conv:
        conv = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer["id"],
            "primary_channel": "SMS",
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.conversations.insert_one(conv)

    msg = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "conversation_id": conv["id"],
        "customer_id": customer["id"],
        "direction": "INBOUND",
        "sender_type": "CUSTOMER",
        "channel": "SMS",
        "content": f"[Portal] Reschedule Request for job {job_id}: {message}",
        "is_call_summary": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.messages.insert_one(msg)

    await db.conversations.update_one(
        {"id": conv["id"]},
        {"$set": {
            "last_message_from": "CUSTOMER",
            "last_message_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return {"success": True, "message": "Reschedule request submitted"}


@router.post("/{token}/review")
async def submit_review(token: str, job_id: str, rating: int, comment: Optional[str] = None):
    """Customer submits a review for a completed job"""
    customer = await db.customers.find_one({"portal_token": token})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    job = await db.jobs.find_one({"id": job_id, "customer_id": customer["id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Can only review completed jobs")

    existing_review = await db.reviews.find_one({"job_id": job_id, "customer_id": customer["id"]})
    if existing_review:
        raise HTTPException(status_code=400, detail="Job already reviewed")

    review = {
        "id": str(uuid4()),
        "tenant_id": customer["tenant_id"],
        "customer_id": customer["id"],
        "job_id": job_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.reviews.insert_one(review)

    return {"success": True, "review_id": review["id"]}


@router.post("/{token}/add-note")
async def add_customer_note(token: str, note: str, job_id: Optional[str] = None):
    """Customer adds a note (general or for a specific job)"""
    customer = await db.customers.find_one({"portal_token": token})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    tenant_id = customer["tenant_id"]

    if job_id:
        job = await db.jobs.find_one({"id": job_id, "customer_id": customer["id"]})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    conv = await db.conversations.find_one({
        "customer_id": customer["id"],
        "tenant_id": tenant_id,
        "status": "OPEN"
    })

    if not conv:
        conv = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer["id"],
            "primary_channel": "SMS",
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.conversations.insert_one(conv)

    note_content = f"[Portal Note]"
    if job_id:
        note_content += f" (Job: {job_id})"
    note_content += f": {note}"

    msg = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "conversation_id": conv["id"],
        "customer_id": customer["id"],
        "direction": "INBOUND",
        "sender_type": "CUSTOMER",
        "channel": "SMS",
        "content": note_content,
        "is_call_summary": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.messages.insert_one(msg)

    await db.conversations.update_one(
        {"id": conv["id"]},
        {"$set": {
            "last_message_from": "CUSTOMER",
            "last_message_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return {"success": True, "message": "Note added successfully"}


@router.post("/{token}/request-service")
async def portal_request_service(
    token: str,
    issue_description: str,
    urgency: str = "ROUTINE",
    property_id: Optional[str] = None,
    preferred_date: Optional[str] = None,
    preferred_time_slot: Optional[str] = None
):
    """Customer requests service from portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    tenant_id = customer["tenant_id"]
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})

    valid_urgencies = ["EMERGENCY", "URGENT", "ROUTINE"]
    if urgency not in valid_urgencies:
        urgency = "ROUTINE"

    service_request = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "issue_description": issue_description,
        "urgency": urgency,
        "preferred_date": preferred_date,
        "preferred_time_slot": preferred_time_slot,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.service_requests.insert_one(service_request)

    # Also create a lead from this request
    lead = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "source": "PORTAL_REQUEST",
        "channel": "FORM",
        "status": "NEW",
        "issue_type": issue_description[:100] if len(issue_description) > 100 else issue_description,
        "urgency": urgency,
        "description": issue_description,
        "caller_name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
        "caller_phone": customer.get("phone"),
        "tags": ["portal_request"],
        "first_contact_at": datetime.now(timezone.utc).isoformat(),
        "last_activity_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.leads.insert_one(lead)

    # Send confirmation SMS
    from services.twilio_service import twilio_service

    confirm_msg = f"Hi {customer.get('first_name')}! We received your service request. A team member will contact you shortly to schedule an appointment."
    if tenant.get("sms_signature"):
        confirm_msg += f" {tenant['sms_signature']}"

    await twilio_service.send_sms(
        to_phone=customer["phone"],
        body=confirm_msg
    )

    return {
        "success": True,
        "service_request_id": service_request["id"],
        "lead_id": lead["id"],
        "message": "Service request submitted successfully"
    }


@router.put("/{token}/profile")
async def update_portal_profile(
    token: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None
):
    """Customer updates their profile from portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")

    update_data = {}
    if first_name:
        update_data["first_name"] = first_name
    if last_name:
        update_data["last_name"] = last_name
    if email:
        update_data["email"] = email
    if phone:
        update_data["phone"] = normalize_phone_e164(phone)

    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.customers.update_one(
            {"id": customer["id"]},
            {"$set": update_data}
        )

    updated_customer = await db.customers.find_one({"id": customer["id"]}, {"_id": 0})
    return {
        "success": True,
        "customer": {
            "first_name": updated_customer.get("first_name"),
            "last_name": updated_customer.get("last_name"),
            "email": updated_customer.get("email"),
            "phone": updated_customer.get("phone")
        }
    }
