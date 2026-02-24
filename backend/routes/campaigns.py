"""Campaigns routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs
from models import (
    Campaign, CampaignCreate, CampaignRecipient,
    CampaignStatus, RecipientStatus,
    Message, MessageDirection, SenderType, PreferredChannel,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_campaigns(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List campaigns"""
    campaigns = await db.campaigns.find(
        {"tenant_id": tenant_id}, {"_id": 0}
    ).to_list(100)
    return serialize_docs(campaigns)


@router.post("")
async def create_campaign(
    data: CampaignCreate,
    tenant_id: Optional[str] = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new campaign"""
    # For superadmin without tenant_id, require it to be specified
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for campaign creation")

    campaign = Campaign(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )

    campaign_dict = campaign.model_dump(mode='json')
    await db.campaigns.insert_one(campaign_dict)

    return serialize_doc(campaign_dict)


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: CampaignCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update campaign"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.campaigns.update_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return serialize_doc(campaign)


@router.post("/{campaign_id}/preview-segment")
async def preview_campaign_segment(
    campaign_id: str,
    segment: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Preview customers matching segment criteria.
    segment can include:
    - last_service_days_ago: ">90", ">180", etc.
    - service_type: "HVAC", "Plumbing", etc.
    - customer_status: "active", "inactive"
    """
    import pytz

    # Get tenant timezone
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")

    now = datetime.now(tenant_tz)

    # Build query based on segment
    customer_ids = set()

    # Get customers based on last service date
    last_service_days = segment.get("last_service_days_ago", "")
    if last_service_days:
        # Parse ">90", ">180", etc.
        try:
            days = int(last_service_days.replace(">", "").replace("<", "").strip())
            cutoff_date = now - timedelta(days=days)

            # Find customers with jobs completed before cutoff
            if last_service_days.startswith(">"):
                # Last service MORE than X days ago
                pipeline = [
                    {"$match": {"tenant_id": tenant_id, "status": "COMPLETED"}},
                    {"$sort": {"service_window_start": -1}},
                    {"$group": {
                        "_id": "$customer_id",
                        "last_service": {"$first": "$service_window_start"}
                    }},
                    {"$match": {"last_service": {"$lt": cutoff_date.isoformat()}}}
                ]
            else:
                # Last service LESS than X days ago
                pipeline = [
                    {"$match": {"tenant_id": tenant_id, "status": "COMPLETED"}},
                    {"$sort": {"service_window_start": -1}},
                    {"$group": {
                        "_id": "$customer_id",
                        "last_service": {"$first": "$service_window_start"}
                    }},
                    {"$match": {"last_service": {"$gte": cutoff_date.isoformat()}}}
                ]

            async for doc in db.jobs.aggregate(pipeline):
                if doc["_id"]:
                    customer_ids.add(doc["_id"])
        except:
            pass

    # If no service filter, get all customers with at least one completed job
    if not last_service_days:
        jobs = await db.jobs.distinct("customer_id", {"tenant_id": tenant_id, "status": "COMPLETED"})
        customer_ids = set(jobs)

    # Get customer details
    if not customer_ids:
        # Fallback: get all customers if no filter matched
        customers = await db.customers.find(
            {"tenant_id": tenant_id},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1}
        ).to_list(500)
    else:
        customers = await db.customers.find(
            {"tenant_id": tenant_id, "id": {"$in": list(customer_ids)}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1}
        ).to_list(500)

    # Filter out customers without phone numbers
    customers_with_phone = [c for c in customers if c.get("phone")]

    return {
        "total_matching": len(customers_with_phone),
        "sample_customers": customers_with_phone[:10],  # Return first 10 as preview
        "segment_applied": segment
    }


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Start a campaign: query matching customers, create recipients, and begin sending.
    """
    import pytz
    from services.twilio_service import twilio_service

    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign["status"] not in ["DRAFT", "PAUSED"]:
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign['status']}")

    # Get tenant for Twilio config
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="Tenant Twilio configuration missing")

    tenant_tz_str = tenant.get("timezone", "America/New_York")
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")

    now = datetime.now(tenant_tz)
    segment = campaign.get("segment_definition") or {}

    # Build recipient list based on segment
    customer_ids = set()

    last_service_days = segment.get("last_service_days_ago") or segment.get("lastServiceDaysAgo", "")
    if last_service_days:
        try:
            days = int(str(last_service_days).replace(">", "").replace("<", "").strip())
            cutoff_date = now - timedelta(days=days)

            pipeline = [
                {"$match": {"tenant_id": tenant_id, "status": "COMPLETED"}},
                {"$sort": {"service_window_start": -1}},
                {"$group": {
                    "_id": "$customer_id",
                    "last_service": {"$first": "$service_window_start"}
                }},
                {"$match": {"last_service": {"$lt": cutoff_date.isoformat()}}}
            ]

            async for doc in db.jobs.aggregate(pipeline):
                if doc["_id"]:
                    customer_ids.add(doc["_id"])
        except:
            pass

    # If no segment or empty results, get all customers with completed jobs
    if not customer_ids:
        jobs = await db.jobs.distinct("customer_id", {"tenant_id": tenant_id, "status": "COMPLETED"})
        customer_ids = set(jobs) if jobs else set()

    # If still empty, get all customers
    if not customer_ids:
        all_customers = await db.customers.find(
            {"tenant_id": tenant_id},
            {"_id": 0, "id": 1}
        ).to_list(500)
        customer_ids = set(c["id"] for c in all_customers)

    # Get customer details and create recipients
    customers = await db.customers.find(
        {"tenant_id": tenant_id, "id": {"$in": list(customer_ids)}},
        {"_id": 0}
    ).to_list(500)

    # Filter customers with phone numbers
    customers_with_phone = [c for c in customers if c.get("phone")]

    # Delete existing recipients for this campaign (in case of restart)
    await db.campaign_recipients.delete_many({"campaign_id": campaign_id})

    # Create recipient records
    recipients_created = 0
    for customer in customers_with_phone:
        recipient = CampaignRecipient(
            campaign_id=campaign_id,
            customer_id=customer["id"],
            status=RecipientStatus.PENDING
        )
        recipient_dict = recipient.model_dump(mode='json')
        await db.campaign_recipients.insert_one(recipient_dict)
        recipients_created += 1

    # Update campaign status
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": CampaignStatus.RUNNING.value,
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "total_recipients": recipients_created
        }}
    )

    return {
        "status": "started",
        "campaign_id": campaign_id,
        "recipients_created": recipients_created,
        "message": f"Campaign started with {recipients_created} recipients. Messages will be sent in batches."
    }


@router.post("/{campaign_id}/send-batch")
async def send_campaign_batch(
    campaign_id: str,
    batch_size: int = 10,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a batch of campaign messages. Call repeatedly to send all messages.
    """
    from services.twilio_service import twilio_service

    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign["status"] != "RUNNING":
        raise HTTPException(status_code=400, detail="Campaign is not running")

    # Get tenant for Twilio
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="Tenant Twilio configuration missing")

    from_phone = tenant["twilio_phone_number"]
    message_template = campaign.get("message_template", "")

    # Get pending recipients
    pending_recipients = await db.campaign_recipients.find(
        {"campaign_id": campaign_id, "status": RecipientStatus.PENDING.value}
    ).to_list(batch_size)

    if not pending_recipients:
        # Mark campaign as completed if no more pending
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {"status": CampaignStatus.COMPLETED.value, "completed_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"status": "completed", "sent_in_batch": 0, "remaining": 0}

    sent_count = 0
    errors = []

    for recipient in pending_recipients:
        # Get customer
        customer = await db.customers.find_one(
            {"id": recipient["customer_id"]},
            {"_id": 0}
        )
        if not customer or not customer.get("phone"):
            await db.campaign_recipients.update_one(
                {"id": recipient["id"]},
                {"$set": {"status": RecipientStatus.OPTED_OUT.value, "error": "No phone number"}}
            )
            continue

        # Personalize message
        message = message_template
        message = message.replace("{first_name}", customer.get("first_name", ""))
        message = message.replace("{last_name}", customer.get("last_name", ""))
        message = message.replace("{company_name}", tenant.get("name", ""))

        try:
            # Send SMS
            result = await twilio_service.send_sms(
                to_phone=customer["phone"],
                body=message,
                from_phone=from_phone
            )

            # Update recipient status
            await db.campaign_recipients.update_one(
                {"id": recipient["id"]},
                {"$set": {
                    "status": RecipientStatus.SENT.value,
                    "last_message_at": datetime.now(timezone.utc).isoformat(),
                    "twilio_sid": result.get("provider_message_id")
                }}
            )
            sent_count += 1

            # Store message in conversation for tracking
            conv = await db.conversations.find_one(
                {"customer_id": customer["id"], "tenant_id": tenant_id},
                {"_id": 0}
            )
            if conv:
                msg = Message(
                    tenant_id=tenant_id,
                    conversation_id=conv["id"],
                    customer_id=customer["id"],
                    direction=MessageDirection.OUTBOUND,
                    sender_type=SenderType.SYSTEM,
                    channel=PreferredChannel.SMS,
                    content=message
                )
                msg_dict = msg.model_dump(mode='json')
                msg_dict["metadata"] = {"campaign_id": campaign_id, "twilio_sid": result.get("provider_message_id")}
                await db.messages.insert_one(msg_dict)

            # Also log to campaign_messages collection for campaign-specific tracking
            campaign_msg = {
                "id": str(uuid4()),
                "campaign_id": campaign_id,
                "tenant_id": tenant_id,
                "customer_id": customer["id"],
                "direction": "OUTBOUND",
                "content": message,
                "twilio_sid": result.get("provider_message_id"),
                "status": "SENT",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.campaign_messages.insert_one(campaign_msg)

        except Exception as e:
            errors.append({"customer_id": recipient["customer_id"], "error": str(e)})
            await db.campaign_recipients.update_one(
                {"id": recipient["id"]},
                {"$set": {"status": RecipientStatus.OPTED_OUT.value, "error": str(e)}}
            )

    # Get remaining count
    remaining = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.PENDING.value}
    )

    return {
        "status": "sending",
        "sent_in_batch": sent_count,
        "errors": len(errors),
        "remaining": remaining,
        "error_details": errors[:5] if errors else []
    }


@router.get("/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get real-time campaign statistics"""
    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Count recipients by status
    total = await db.campaign_recipients.count_documents({"campaign_id": campaign_id})
    pending = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.PENDING.value}
    )
    sent = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.SENT.value}
    )
    responded = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.RESPONDED.value}
    )
    opted_out = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.OPTED_OUT.value}
    )

    # Calculate response rate
    response_rate = (responded / sent * 100) if sent > 0 else 0

    # Get recipients list
    recipients = await db.campaign_recipients.find(
        {"campaign_id": campaign_id},
        {"_id": 0}
    ).to_list(100)

    # Enrich with customer data
    enriched_recipients = []
    for r in recipients:
        customer = await db.customers.find_one({"id": r["customer_id"]}, {"_id": 0})
        if customer:
            enriched_recipients.append({
                **r,
                "customer_name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                "customer_phone": customer.get("phone", "")
            })

    return {
        "campaign_id": campaign_id,
        "campaign_status": campaign.get("status"),
        "stats": {
            "total": total,
            "pending": pending,
            "sent": sent,
            "responded": responded,
            "opted_out": opted_out,
            "response_rate": round(response_rate, 1)
        },
        "recipients": enriched_recipients
    }


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a campaign and its recipients"""
    result = await db.campaigns.delete_one({"id": campaign_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Delete associated recipients
    await db.campaign_recipients.delete_many({"campaign_id": campaign_id})

    # Delete associated campaign messages
    await db.campaign_messages.delete_many({"campaign_id": campaign_id})

    return {"status": "deleted", "campaign_id": campaign_id}


@router.post("/bulk-delete")
async def bulk_delete_campaigns(
    campaign_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete multiple campaigns at once"""
    deleted_count = 0
    for campaign_id in campaign_ids:
        result = await db.campaigns.delete_one({"id": campaign_id, "tenant_id": tenant_id})
        if result.deleted_count > 0:
            await db.campaign_recipients.delete_many({"campaign_id": campaign_id})
            await db.campaign_messages.delete_many({"campaign_id": campaign_id})
            deleted_count += 1

    return {"status": "deleted", "deleted_count": deleted_count}


@router.get("/customers-for-selection")
async def get_customers_for_campaign_selection(
    job_type: Optional[str] = None,
    last_service_days: Optional[int] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Get customers filtered by job type for campaign selection.
    job_type: DIAGNOSTIC, REPAIR, MAINTENANCE, INSTALLATION
    last_service_days: Filter by last service more than X days ago
    """
    import pytz

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")

    now = datetime.now(tenant_tz)

    # Build job filter
    job_filter = {"tenant_id": tenant_id, "status": "COMPLETED"}
    if job_type:
        job_filter["job_type"] = job_type.upper()

    # Get customers with matching jobs
    pipeline = [
        {"$match": job_filter},
        {"$sort": {"service_window_start": -1}},
        {"$group": {
            "_id": "$customer_id",
            "last_service": {"$first": "$service_window_start"},
            "job_types": {"$addToSet": "$job_type"},
            "job_count": {"$sum": 1}
        }}
    ]

    # Add date filter if specified
    if last_service_days:
        cutoff_date = now - timedelta(days=last_service_days)
        pipeline.append({"$match": {"last_service": {"$lt": cutoff_date.isoformat()}}})

    job_data = {}
    async for doc in db.jobs.aggregate(pipeline):
        if doc["_id"]:
            job_data[doc["_id"]] = {
                "last_service": doc["last_service"],
                "job_types": doc["job_types"],
                "job_count": doc["job_count"]
            }

    # Get customer details
    if job_data:
        customers = await db.customers.find(
            {"tenant_id": tenant_id, "id": {"$in": list(job_data.keys())}},
            {"_id": 0}
        ).to_list(500)
    else:
        # If no filter, get all customers
        customers = await db.customers.find(
            {"tenant_id": tenant_id},
            {"_id": 0}
        ).to_list(500)

    # Enrich with job data
    enriched_customers = []
    for c in customers:
        if c.get("phone"):  # Only include customers with phone
            customer_job_data = job_data.get(c["id"], {})
            enriched_customers.append({
                "id": c["id"],
                "first_name": c.get("first_name", ""),
                "last_name": c.get("last_name", ""),
                "phone": c.get("phone", ""),
                "email": c.get("email", ""),
                "last_service": customer_job_data.get("last_service"),
                "job_types": customer_job_data.get("job_types", []),
                "job_count": customer_job_data.get("job_count", 0)
            })

    # Get available job types for filter dropdown
    all_job_types = await db.jobs.distinct("job_type", {"tenant_id": tenant_id})

    return {
        "customers": enriched_customers,
        "total": len(enriched_customers),
        "available_job_types": all_job_types,
        "filters_applied": {
            "job_type": job_type,
            "last_service_days": last_service_days
        }
    }


@router.post("/{campaign_id}/start-with-customers")
async def start_campaign_with_selected_customers(
    campaign_id: str,
    customer_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Start a campaign with manually selected customers.
    """
    import pytz

    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign["status"] not in ["DRAFT", "PAUSED"]:
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign['status']}")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")

    now = datetime.now(tenant_tz)

    # Get customer details
    customers = await db.customers.find(
        {"tenant_id": tenant_id, "id": {"$in": customer_ids}},
        {"_id": 0}
    ).to_list(len(customer_ids))

    # Filter customers with phone numbers
    customers_with_phone = [c for c in customers if c.get("phone")]

    # Delete existing recipients for this campaign (in case of restart)
    await db.campaign_recipients.delete_many({"campaign_id": campaign_id})

    # Create recipient records
    recipients_created = 0
    for customer in customers_with_phone:
        recipient = CampaignRecipient(
            campaign_id=campaign_id,
            customer_id=customer["id"],
            status=RecipientStatus.PENDING
        )
        recipient_dict = recipient.model_dump(mode='json')
        await db.campaign_recipients.insert_one(recipient_dict)
        recipients_created += 1

    # Update campaign status
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": CampaignStatus.RUNNING.value,
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "total_recipients": recipients_created,
            "selection_type": "manual",
            "selected_customer_ids": customer_ids
        }}
    )

    return {
        "status": "started",
        "campaign_id": campaign_id,
        "recipients_created": recipients_created,
        "message": f"Campaign started with {recipients_created} manually selected recipients."
    }


@router.get("/{campaign_id}/messages")
async def get_campaign_messages(
    campaign_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all SMS messages (outbound and inbound) for a specific campaign.
    """
    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get campaign messages from dedicated collection
    messages = await db.campaign_messages.find(
        {"campaign_id": campaign_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    # Enrich with customer data
    enriched_messages = []
    for msg in messages:
        customer = await db.customers.find_one(
            {"id": msg.get("customer_id")},
            {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1}
        )
        enriched_messages.append({
            **msg,
            "customer_name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() if customer else "Unknown",
            "customer_phone": customer.get("phone", "") if customer else ""
        })

    # Get stats
    outbound_count = len([m for m in messages if m.get("direction") == "OUTBOUND"])
    inbound_count = len([m for m in messages if m.get("direction") == "INBOUND"])

    return {
        "campaign_id": campaign_id,
        "messages": enriched_messages,
        "stats": {
            "total": len(messages),
            "outbound": outbound_count,
            "inbound": inbound_count
        }
    }
