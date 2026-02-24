"""Web Form routes - public endpoint for lead submission from web forms"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4
import logging

from core.database import db
from core.utils import serialize_doc, normalize_phone_e164
from models import (
    Lead, LeadSource, LeadChannel, LeadStatus, Urgency,
    Customer,
    Message, MessageDirection, SenderType, PreferredChannel,
    Conversation, ConversationStatus,
    WebFormLeadRequest,
    Job, JobType, JobStatus, JobPriority, JobCreatedBy,
    Quote, QuoteStatus,
)

router = APIRouter(prefix="/webform", tags=["webform"])
logger = logging.getLogger(__name__)


@router.post("/submit")
async def submit_web_form(data: WebFormLeadRequest):
    """
    Public endpoint for web form lead submission.
    Creates lead, customer, and optionally sends SMS confirmation.

    No authentication required - use tenant_slug to identify the business.

    Example request:
    POST /api/v1/webform/submit
    {
        "tenant_slug": "radiance-hvac",
        "name": "John Smith",
        "phone": "+12155551234",
        "email": "john@example.com",
        "address": "123 Main St",
        "city": "Philadelphia",
        "state": "PA",
        "zip_code": "19001",
        "issue_description": "AC not cooling properly",
        "urgency": "URGENT",
        "send_confirmation_sms": true
    }
    """
    from services.twilio_service import twilio_service
    import pytz

    # Get tenant by slug
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Business not found")

    tenant_id = tenant["id"]
    tenant_tz_str = tenant.get("timezone", "America/New_York")
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")

    now = datetime.now(tenant_tz)

    # Normalize phone number to E.164 format
    phone = normalize_phone_e164(data.phone)

    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")

    # Parse name
    name_parts = data.name.strip().split(' ', 1) if data.name else ["Unknown"]
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Find or create customer
    customer = await db.customers.find_one({"phone": phone, "tenant_id": tenant_id}, {"_id": 0})

    if not customer:
        customer_id = str(uuid4())
        customer = {
            "id": customer_id,
            "tenant_id": tenant_id,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "email": data.email if data.email else None,
            "preferred_channel": "SMS",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.customers.insert_one(customer)
        logger.info(f"Created customer from web form: {customer_id}")
    else:
        customer_id = customer["id"]
        # Update email if provided and not set
        if data.email and not customer.get("email"):
            await db.customers.update_one(
                {"id": customer_id},
                {"$set": {"email": data.email, "updated_at": now.isoformat()}}
            )

    # Create property if address provided
    property_id = None
    if data.address:
        property_id = str(uuid4())
        prop = {
            "id": property_id,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "address_line1": data.address,
            "city": data.city or "",
            "state": data.state or "",
            "postal_code": data.zip_code or "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.properties.insert_one(prop)

    # Create lead
    lead_id = str(uuid4())
    urgency_value = data.urgency.upper() if data.urgency else "ROUTINE"
    if urgency_value not in ["EMERGENCY", "URGENT", "ROUTINE"]:
        urgency_value = "ROUTINE"

    lead = Lead(
        tenant_id=tenant_id,
        customer_id=customer_id,
        property_id=property_id,
        source=LeadSource.WEB_FORM,
        channel=LeadChannel.FORM,
        status=LeadStatus.NEW,
        urgency=Urgency(urgency_value),
        description=data.issue_description,
        caller_name=data.name,
        caller_phone=phone
    )
    lead_dict = lead.model_dump(mode='json')
    lead_dict["id"] = lead_id

    # Add preferred scheduling if provided
    if data.preferred_date:
        lead_dict["preferred_date"] = data.preferred_date
    if data.preferred_time:
        lead_dict["preferred_time"] = data.preferred_time

    await db.leads.insert_one(lead_dict)
    logger.info(f"Created lead from web form: {lead_id}")

    # Create or get conversation
    conv = await db.conversations.find_one(
        {"customer_id": customer_id, "tenant_id": tenant_id},
        {"_id": 0}
    )

    if not conv:
        conv_id = str(uuid4())
        conv = {
            "id": conv_id,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "status": "OPEN",
            "primary_channel": "SMS",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.conversations.insert_one(conv)
    else:
        conv_id = conv["id"]

    # Send AI-powered initial SMS to start booking conversation
    sms_sent = False
    sms_error = None

    if data.send_confirmation_sms and tenant.get("twilio_phone_number"):
        try:
            from services.ai_sms_service import ai_sms_service

            company_name = tenant.get("name", "Our company")

            # Generate AI-powered initial message
            initial_msg = await ai_sms_service.generate_initial_message(
                customer_name=first_name,
                issue_description=data.issue_description or "service request",
                company_name=company_name
            )

            result = await twilio_service.send_sms(
                to_phone=phone,
                body=initial_msg,
                from_phone=tenant["twilio_phone_number"]
            )
            sms_sent = True

            # Store outbound message and mark conversation for AI handling
            msg = Message(
                tenant_id=tenant_id,
                conversation_id=conv_id,
                customer_id=customer_id,
                direction=MessageDirection.OUTBOUND,
                sender_type=SenderType.AI,
                channel=PreferredChannel.SMS,
                content=initial_msg
            )
            msg_dict = msg.model_dump(mode='json')
            msg_dict["metadata"] = {
                "source": "web_form_ai_booking",
                "lead_id": lead_id,
                "ai_booking_active": True
            }
            await db.messages.insert_one(msg_dict)

            # Update conversation to track AI booking state
            await db.conversations.update_one(
                {"id": conv_id},
                {"$set": {
                    "ai_booking_active": True,
                    "ai_booking_lead_id": lead_id,
                    "ai_booking_context": {
                        "customer_name": f"{first_name} {last_name}".strip(),
                        "issue_description": data.issue_description,
                        "urgency": urgency_value,
                        "address": f"{data.address or ''}, {data.city or ''}, {data.state or ''} {data.zip_code or ''}".strip(", "),
                        "property_id": property_id
                    },
                    "updated_at": now.isoformat()
                }}
            )

            logger.info(f"Started AI booking conversation for web form lead {lead_id}")

        except Exception as e:
            logger.error(f"Failed to start AI SMS conversation: {str(e)}")
            sms_error = str(e)

    return {
        "success": True,
        "lead_id": lead_id,
        "customer_id": customer_id,
        "property_id": property_id,
        "conversation_id": conv_id,
        "sms_sent": sms_sent,
        "sms_error": sms_error,
        "message": f"Thank you, {first_name}! Your request has been received. {'We sent a confirmation to your phone.' if sms_sent else 'We will contact you shortly.'}"
    }
