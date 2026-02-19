"""Jobs routes - full CRUD plus en-route, on-my-way, complete, request-review"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging
import secrets

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs, calculate_quote_amount
from models import (
    Job, JobCreate, JobStatus, JobType, JobPriority, JobCreatedBy,
    Quote, QuoteStatus,
    Invoice, InvoiceCreate, InvoiceStatus,
    LeadStatus,
    Message, MessageDirection, SenderType,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


class OnMyWayRequest(BaseModel):
    eta_minutes: int = 30
    custom_message: Optional[str] = None
    send_sms: bool = True
    include_tracking_link: bool = True


class EnRouteRequest(BaseModel):
    technician_id: Optional[str] = None
    estimated_minutes: int = 30
    send_sms: bool = True
    include_tracking_link: bool = True


class ArrivedRequest(BaseModel):
    technician_id: Optional[str] = None


class CompletionPhoto(BaseModel):
    type: str = "OTHER"  # BEFORE, AFTER, OTHER
    url: str
    caption: Optional[str] = None


class AdditionalCharge(BaseModel):
    description: str
    amount: float


class JobCompleteRequest(BaseModel):
    technician_id: Optional[str] = None
    completion_notes: Optional[str] = None
    photos: Optional[List[CompletionPhoto]] = None
    signature_url: Optional[str] = None
    additional_charges: Optional[List[AdditionalCharge]] = None
    send_invoice: bool = True
    request_review: bool = True


class ReviewRequestPayload(BaseModel):
    platform: str = "google"


@router.get("")
async def list_jobs(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List jobs with optional filters"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    if date_from:
        query["service_window_start"] = {"$gte": date_from}
    if date_to:
        if "service_window_start" in query:
            query["service_window_start"]["$lte"] = date_to
        else:
            query["service_window_start"] = {"$lte": date_to}

    jobs = await db.jobs.find(query, {"_id": 0}).sort("service_window_start", 1).to_list(1000)

    # Enrich with customer and property info
    for job in jobs:
        customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
        prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
        tech = None
        if job.get("assigned_technician_id"):
            tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0})

        job["customer"] = serialize_doc(customer) if customer else None
        job["property"] = serialize_doc(prop) if prop else None
        job["technician"] = serialize_doc(tech) if tech else None

    return serialize_docs(jobs)


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get job details"""
    job = await db.jobs.find_one(
        {"id": job_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
    prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
    tech = None
    if job.get("assigned_technician_id"):
        tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0})

    return {
        **serialize_doc(job),
        "customer": serialize_doc(customer) if customer else None,
        "property": serialize_doc(prop) if prop else None,
        "technician": serialize_doc(tech) if tech else None
    }


@router.post("")
async def create_job(
    data: JobCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new job"""
    # Verify customer and property exist
    customer = await db.customers.find_one({"id": data.customer_id, "tenant_id": tenant_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    prop = await db.properties.find_one({"id": data.property_id, "tenant_id": tenant_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # Get lead urgency for quote calculation if not already provided
    job_data = data.model_dump(mode='json')
    if not job_data.get("quote_amount") and data.lead_id:
        lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0, "urgency": 1})
        lead_urgency = lead.get("urgency") if lead else None
        job_data["quote_amount"] = calculate_quote_amount(job_data.get("job_type", "DIAGNOSTIC"), lead_urgency)
    elif not job_data.get("quote_amount"):
        # Calculate based on job type and priority
        priority_to_urgency = {"EMERGENCY": "EMERGENCY", "HIGH": "URGENT", "NORMAL": "ROUTINE"}
        urgency = priority_to_urgency.get(job_data.get("priority", "NORMAL"), "ROUTINE")
        job_data["quote_amount"] = calculate_quote_amount(job_data.get("job_type", "DIAGNOSTIC"), urgency)

    job = Job(
        tenant_id=tenant_id,
        **job_data
    )

    job_dict = job.model_dump(mode='json')
    await db.jobs.insert_one(job_dict)

    # Create a Quote record linked to the job (if quote_amount exists)
    if job_dict.get("quote_amount"):
        lead_data = None
        if data.lead_id:
            lead_data = await db.leads.find_one({"id": data.lead_id}, {"_id": 0})

        quote_description = f"{job_dict.get('job_type', 'Service')} service"
        if lead_data:
            if lead_data.get("issue_type"):
                quote_description = f"{job_dict.get('job_type')} - {lead_data.get('issue_type')}"
            if lead_data.get("description"):
                quote_description += f"\n{lead_data.get('description')}"

        quote = Quote(
            tenant_id=tenant_id,
            customer_id=data.customer_id,
            property_id=data.property_id,
            job_id=job.id,
            amount=job_dict["quote_amount"],
            description=quote_description,
            status=QuoteStatus.SENT
        )

        quote_dict = quote.model_dump(mode='json')
        quote_dict["sent_at"] = datetime.now(timezone.utc).isoformat()
        await db.quotes.insert_one(quote_dict)

        # Link quote to job
        job_dict["quote_id"] = quote.id
        await db.jobs.update_one(
            {"id": job.id},
            {"$set": {"quote_id": quote.id}}
        )

        # Send quote SMS to customer
        tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
        if tenant and tenant.get("twilio_phone_number"):
            from services.twilio_service import twilio_service

            # Send quote SMS (continuation, no greeting)
            sms_sig = tenant.get('sms_signature', '').strip()
            quote_message = f"Your service quote for {job_dict.get('job_type', 'service')} is ${job_dict['quote_amount']:.2f}. Pay securely here: [YOUR PAYMENT LINK HERE]. Reply with any questions!{' ' + sms_sig if sms_sig else ''}"

            await twilio_service.send_sms(
                to_phone=customer["phone"],
                body=quote_message,
                from_phone=tenant["twilio_phone_number"]
            )

    # Update lead status if linked
    if data.lead_id:
        await db.leads.update_one(
            {"id": data.lead_id, "tenant_id": tenant_id},
            {"$set": {"status": LeadStatus.JOB_BOOKED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

    return serialize_doc(job_dict)


@router.put("/{job_id}")
async def update_job(
    job_id: str,
    data: JobCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update job"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["service_window_start"] = update_data["service_window_start"].isoformat()
    update_data["service_window_end"] = update_data["service_window_end"].isoformat()
    if update_data.get("exact_arrival_time"):
        update_data["exact_arrival_time"] = update_data["exact_arrival_time"].isoformat()

    result = await db.jobs.update_one(
        {"id": job_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")

    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return serialize_doc(job)


@router.post("/{job_id}/en-route")
async def mark_job_en_route(
    job_id: str,
    data: EnRouteRequest = EnRouteRequest(),
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Mark job as en-route, generate tracking token, and send SMS"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Generate tracking token and calculate ETA
    tracking_token = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    estimated_arrival = (now + timedelta(minutes=data.estimated_minutes)).isoformat()

    tech_id = data.technician_id or job.get("assigned_technician_id")

    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": JobStatus.EN_ROUTE.value,
            "en_route_at": now.isoformat(),
            "en_route_sms_sent": True,
            "tracking_token": tracking_token,
            "estimated_arrival": estimated_arrival,
            "assigned_technician_id": tech_id,
            "updated_at": now.isoformat()
        }}
    )

    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    sms_sent = False

    if data.send_sms and customer and tenant and tenant.get("twilio_phone_number"):
        from services.twilio_service import twilio_service

        tech = None
        if tech_id:
            tech = await db.technicians.find_one({"id": tech_id}, {"_id": 0})

        tech_name = (tech.get("name") if tech else None) or "Your technician"
        eta_time = (now + timedelta(minutes=data.estimated_minutes)).strftime("%-I:%M %p")

        message = (
            f"Hi {customer.get('first_name', 'there')}! "
            f"{tech_name} from {tenant['name']} is on the way. "
            f"Estimated arrival: {eta_time} (~{data.estimated_minutes} min)."
        )
        if data.include_tracking_link:
            base_url = tenant.get("app_url", "https://app.fieldos.com")
            message += f" Track: {base_url}/track/{tracking_token}"
        if tenant.get("sms_signature"):
            message += f" {tenant['sms_signature']}"

        result = await twilio_service.send_sms(
            to_phone=customer["phone"],
            body=message,
            from_phone=tenant["twilio_phone_number"]
        )
        sms_sent = result.get("success", False)

        if sms_sent:
            msg = Message(
                tenant_id=tenant_id,
                conversation_id="",
                customer_id=customer["id"],
                direction=MessageDirection.OUTBOUND,
                sender_type=SenderType.SYSTEM,
                content=message,
                metadata={"twilio_sid": result.get("provider_message_id")}
            )
            await db.messages.insert_one(msg.model_dump(mode='json'))

    return {"success": True, "sms_sent": sms_sent, "tracking_token": tracking_token}


@router.post("/{job_id}/arrived")
async def mark_job_arrived(
    job_id: str,
    data: ArrivedRequest = ArrivedRequest(),
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Mark technician as arrived on site"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    now = datetime.now(timezone.utc)
    tech_id = data.technician_id or job.get("assigned_technician_id")

    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": JobStatus.IN_PROGRESS.value,
            "actual_arrival": now.isoformat(),
            "assigned_technician_id": tech_id,
            "updated_at": now.isoformat()
        }}
    )

    return {"success": True, "arrived_at": now.isoformat()}


@router.post("/{job_id}/on-my-way")
async def send_on_my_way(
    job_id: str,
    data: OnMyWayRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send 'On My Way' SMS with custom ETA"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured")

    tech = await db.technicians.find_one({"id": job.get("assigned_technician_id")}, {"_id": 0}) if job.get("assigned_technician_id") else None
    tech_name = tech.get("name", "Your technician") if tech else "Your technician"

    if data.custom_message:
        message = data.custom_message
    else:
        message = f"Hi {customer.get('first_name', 'there')}! {tech_name} from {tenant['name']} is on the way and will arrive in approximately {data.eta_minutes} minutes."
        if tenant.get("sms_signature"):
            message += f" {tenant['sms_signature']}"

    from services.twilio_service import twilio_service
    await twilio_service.send_sms(to_phone=customer["phone"], message=message, from_phone=tenant["twilio_phone_number"])

    await db.jobs.update_one({"id": job_id}, {"$set": {"status": JobStatus.EN_ROUTE.value, "en_route_at": datetime.now(timezone.utc).isoformat(), "eta_minutes": data.eta_minutes}})

    return {"success": True, "message": "On My Way notification sent"}


@router.post("/{job_id}/complete")
async def complete_job(
    job_id: str,
    data: JobCompleteRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Complete a job: mark complete, auto-create invoice, send payment SMS, schedule review"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    now = datetime.now(timezone.utc)

    # Build update fields
    update_fields = {
        "status": JobStatus.COMPLETED.value,
        "completed_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    if data.completion_notes:
        update_fields["completion_notes"] = data.completion_notes
    if data.photos:
        update_fields["completion_photos"] = [p.model_dump() for p in data.photos]
    if data.signature_url:
        update_fields["signature_url"] = data.signature_url
    if data.technician_id:
        update_fields["assigned_technician_id"] = data.technician_id

    await db.jobs.update_one({"id": job_id}, {"$set": update_fields})

    invoice_result = None
    invoice_sent = False

    if data.send_invoice and customer:
        # Check if invoice already exists for this job
        existing_invoice = await db.invoices.find_one({"job_id": job_id, "tenant_id": tenant_id})

        if not existing_invoice:
            # Build line items from quote_amount + any additional charges
            line_items = []
            base_amount = job.get("quote_amount", 0) or 0
            if base_amount:
                line_items.append({
                    "description": f"{job.get('job_type', 'Service')} - {data.completion_notes or 'Service completed'}",
                    "quantity": 1,
                    "unit_price": base_amount,
                    "total": base_amount,
                    "type": "LABOR"
                })
            for charge in (data.additional_charges or []):
                line_items.append({
                    "description": charge.description,
                    "quantity": 1,
                    "unit_price": charge.amount,
                    "total": charge.amount,
                    "type": "FEE"
                })

            subtotal = sum(item["total"] for item in line_items)
            invoice_settings = tenant.get("invoice_settings", {}) if tenant else {}
            tax_rate = invoice_settings.get("default_tax_rate", 0)
            tax_amount = round(subtotal * tax_rate / 100, 2)
            total = round(subtotal + tax_amount, 2)

            # Generate invoice number
            next_num = invoice_settings.get("next_invoice_number", 1)
            prefix = invoice_settings.get("invoice_prefix", "INV")
            year = now.year
            invoice_number = f"{prefix}-{year}-{next_num:04d}"
            await db.tenants.update_one(
                {"id": tenant_id},
                {"$set": {"invoice_settings.next_invoice_number": next_num + 1}}
            )

            due_days = invoice_settings.get("default_payment_terms", 10)
            due_date = (now + timedelta(days=due_days)).date().isoformat()

            invoice_doc = {
                "id": str(__import__("uuid").uuid4()),
                "tenant_id": tenant_id,
                "customer_id": job["customer_id"],
                "property_id": job.get("property_id"),
                "job_id": job_id,
                "quote_id": job.get("quote_id"),
                "invoice_number": invoice_number,
                "line_items": line_items,
                "subtotal": subtotal,
                "discount_type": None,
                "discount_value": 0,
                "discount_amount": 0,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "total": total,
                "amount_paid": 0,
                "amount_due": total,
                "status": InvoiceStatus.SENT.value,
                "invoice_date": now.isoformat(),
                "due_date": due_date,
                "sent_at": now.isoformat(),
                "payments": [],
                "notes": invoice_settings.get("invoice_footer_text", ""),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            await db.invoices.insert_one(invoice_doc)
            await db.jobs.update_one({"id": job_id}, {"$set": {"invoice_id": invoice_doc["id"]}})
            invoice_result = invoice_doc

            # Send SMS with payment link
            if tenant and tenant.get("twilio_phone_number") and customer.get("phone"):
                from services.twilio_service import twilio_service
                base_url = tenant.get("app_url", "https://app.fieldos.com")
                payment_token = secrets.token_urlsafe(16)
                await db.invoices.update_one(
                    {"id": invoice_doc["id"]},
                    {"$set": {"payment_link_token": payment_token}}
                )
                payment_link = f"{base_url}/pay/{payment_token}"

                notes_line = f"\nSummary: {data.completion_notes}" if data.completion_notes else ""
                message = (
                    f"Hi {customer.get('first_name', 'there')}! "
                    f"Your {job.get('job_type', 'service')} is complete.{notes_line}\n"
                    f"Invoice #{invoice_number}: ${total:.2f}\n"
                    f"Pay securely: {payment_link}"
                )
                if tenant.get("sms_signature"):
                    message += f" {tenant['sms_signature']}"

                result = await twilio_service.send_sms(
                    to_phone=customer["phone"],
                    body=message,
                    from_phone=tenant["twilio_phone_number"]
                )
                invoice_sent = result.get("success", False)

    # Schedule review request if requested
    review_scheduled_at = None
    if data.request_review and tenant:
        review_settings = tenant.get("review_settings", {})
        delay_hours = review_settings.get("delay_hours", 2)
        review_scheduled_at = (now + timedelta(hours=delay_hours)).isoformat()
        await db.jobs.update_one(
            {"id": job_id},
            {"$set": {"review_scheduled_at": review_scheduled_at}}
        )

    updated_job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return {
        "success": True,
        "job": serialize_doc(updated_job),
        "invoice": serialize_doc(invoice_result) if invoice_result else None,
        "invoice_sent": invoice_sent,
        "review_scheduled": review_scheduled_at is not None,
        "review_send_at": review_scheduled_at,
    }


@router.post("/{job_id}/request-review")
async def request_review(
    job_id: str,
    data: ReviewRequestPayload,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send review request SMS after job completion"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != JobStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Job must be completed")

    customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured")

    branding = tenant.get("branding", {})
    review_urls = {"google": branding.get("google_review_url", ""), "yelp": branding.get("yelp_review_url", ""), "facebook": branding.get("facebook_review_url", "")}
    review_url = review_urls.get(data.platform, "")

    message = f"Hi {customer.get('first_name', 'there')}! Thank you for choosing {tenant['name']}. We hope you're satisfied with our service!"
    if review_url:
        message += f" We'd love your feedback: {review_url}"
    if tenant.get("sms_signature"):
        message += f" {tenant['sms_signature']}"

    from services.twilio_service import twilio_service
    await twilio_service.send_sms(to_phone=customer["phone"], message=message, from_phone=tenant["twilio_phone_number"])

    await db.jobs.update_one({"id": job_id}, {"$set": {"review_requested_at": datetime.now(timezone.utc).isoformat(), "review_platform": data.platform}})

    return {"success": True, "message": "Review request sent"}


@router.post("/bulk-delete")
async def bulk_delete_jobs(
    job_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete jobs"""
    if not job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")

    result = await db.jobs.delete_many({"id": {"$in": job_ids}, "tenant_id": tenant_id})

    return {"success": True, "deleted_count": result.deleted_count}


@router.post("/{job_id}/send-reminder")
async def send_manual_reminder(
    job_id: str,
    reminder_type: str = "day_before",
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Manually send a reminder for a job"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})

    if not customer or not tenant:
        raise HTTPException(status_code=404, detail="Customer or tenant not found")

    from scheduler import send_reminder_sms
    success = await send_reminder_sms(tenant, customer, job, reminder_type)

    if success:
        # Update the appropriate flag
        flag_field = f"reminder_{reminder_type}_sent"
        await db.jobs.update_one(
            {"id": job_id},
            {"$set": {flag_field: True}}
        )

    return {"success": success}
