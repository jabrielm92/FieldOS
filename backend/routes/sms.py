"""SMS Inbound Webhook - Twilio SMS handler"""
from fastapi import APIRouter, Request
from datetime import datetime, timezone
from uuid import uuid4
import logging

from core.database import db
from core.utils import calculate_quote_amount
from models import (
    Customer,
    Message, MessageDirection, SenderType, PreferredChannel,
    Conversation, ConversationStatus,
    RecipientStatus,
    Job, JobType, JobStatus, JobPriority, JobCreatedBy,
    Quote, QuoteStatus,
    LeadStatus,
)

router = APIRouter(prefix="/sms", tags=["sms"])
logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """Normalize phone number to +1XXXXXXXXXX format"""
    if not phone:
        return ""
    # Remove all non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())
    # Add country code if missing
    if len(digits) == 10:
        digits = '1' + digits
    # Add + prefix
    return '+' + digits if digits else ""


@router.post("/inbound")
async def sms_inbound(request: Request):
    """Handle inbound SMS from Twilio webhook"""
    form_data = await request.form()

    from_phone_raw = form_data.get("From", "")
    to_phone_raw = form_data.get("To", "")
    body = form_data.get("Body", "")

    # Normalize phone numbers
    from_phone = normalize_phone(from_phone_raw)
    to_phone = normalize_phone(to_phone_raw)

    logger.info(f"Inbound SMS from {from_phone} to {to_phone}: {body[:50]}...")

    # Find tenant by Twilio phone number (try both normalized and raw)
    tenant = await db.tenants.find_one({"twilio_phone_number": to_phone}, {"_id": 0})
    if not tenant:
        tenant = await db.tenants.find_one({"twilio_phone_number": to_phone_raw}, {"_id": 0})
    if not tenant:
        # Fallback to first tenant for this deployment
        tenant = await db.tenants.find_one({}, {"_id": 0})
        if not tenant:
            logger.error(f"No tenant found for number {to_phone}")
            return {"status": "no_tenant"}

    tenant_id = tenant["id"]

    # Find customer by phone (try multiple formats)
    customer = await db.customers.find_one(
        {"phone": from_phone, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not customer:
        customer = await db.customers.find_one(
            {"phone": from_phone_raw, "tenant_id": tenant_id}, {"_id": 0}
        )
    if not customer:
        # Try regex match on last 10 digits
        phone_digits = ''.join(c for c in from_phone if c.isdigit())[-10:]
        if phone_digits:
            customer = await db.customers.find_one(
                {"phone": {"$regex": phone_digits}, "tenant_id": tenant_id}, {"_id": 0}
            )

    if not customer:
        # Create new customer with normalized phone
        new_customer = Customer(
            tenant_id=tenant_id,
            first_name="Unknown",
            last_name="",
            phone=from_phone
        )
        customer_dict = new_customer.model_dump(mode='json')
        await db.customers.insert_one(customer_dict)
        customer = customer_dict
        logger.info(f"Created new customer for phone {from_phone}")

    # Find or create conversation
    conv = await db.conversations.find_one(
        {"customer_id": customer["id"], "tenant_id": tenant_id, "status": ConversationStatus.OPEN.value},
        {"_id": 0}
    )

    if not conv:
        new_conv = Conversation(
            tenant_id=tenant_id,
            customer_id=customer["id"],
            primary_channel=PreferredChannel.SMS,
            status=ConversationStatus.OPEN
        )
        conv_dict = new_conv.model_dump(mode='json')
        await db.conversations.insert_one(conv_dict)
        conv = conv_dict

    # Create inbound message
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=conv["id"],
        customer_id=customer["id"],
        direction=MessageDirection.INBOUND,
        sender_type=SenderType.CUSTOMER,
        channel=PreferredChannel.SMS,
        content=body
    )
    msg_dict = msg.model_dump(mode='json')
    await db.messages.insert_one(msg_dict)

    # Check if this customer has any active campaign - log as campaign response
    active_recipient = await db.campaign_recipients.find_one({
        "customer_id": customer["id"],
        "status": {"$in": [RecipientStatus.SENT.value, RecipientStatus.PENDING.value]}
    }, {"_id": 0})

    if active_recipient:
        campaign_id = active_recipient.get("campaign_id")

        # Update recipient status to RESPONDED
        await db.campaign_recipients.update_one(
            {"id": active_recipient["id"]},
            {"$set": {
                "status": RecipientStatus.RESPONDED.value,
                "response": body,
                "responded_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        # Log inbound message to campaign_messages
        campaign_msg = {
            "id": str(uuid4()),
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
            "customer_id": customer["id"],
            "direction": "INBOUND",
            "content": body,
            "status": "RECEIVED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.campaign_messages.insert_one(campaign_msg)
        logger.info(f"Campaign response logged from {from_phone} for campaign {campaign_id}")

    # Update conversation
    await db.conversations.update_one(
        {"id": conv["id"]},
        {"$set": {
            "last_message_from": SenderType.CUSTOMER.value,
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    # Check if this is an AI booking conversation (from webform)
    if conv.get("ai_booking_active"):
        try:
            from services.ai_sms_service import ai_sms_service
            import pytz

            # Get conversation history
            history = await db.messages.find(
                {"conversation_id": conv["id"]}, {"_id": 0}
            ).sort("created_at", -1).limit(10).to_list(10)
            history.reverse()

            # Build context for AI
            booking_context = conv.get("ai_booking_context", {})
            booking_context["conversation_id"] = conv["id"]
            booking_context["message_history"] = history

            # Process with AI booking service
            ai_result = await ai_sms_service.process_sms_reply(
                customer_message=body,
                conversation_context=booking_context,
                tenant_info=tenant
            )

            logger.info(f"AI booking result: {ai_result}")

            # Send AI response
            if tenant.get("twilio_phone_number") and ai_result and ai_result.get("response_text"):
                from services.twilio_service import twilio_service

                sms_result = await twilio_service.send_sms(
                    to_phone=from_phone,
                    body=ai_result["response_text"],
                    from_phone=tenant["twilio_phone_number"]
                )

                # Log AI response
                ai_msg = Message(
                    tenant_id=tenant_id,
                    conversation_id=conv["id"],
                    customer_id=customer["id"],
                    direction=MessageDirection.OUTBOUND,
                    sender_type=SenderType.AI,
                    channel=PreferredChannel.SMS,
                    content=ai_result["response_text"],
                    metadata={"twilio_sid": sms_result.get("provider_message_id"), "ai_booking": True}
                )
                ai_msg_dict = ai_msg.model_dump(mode='json')
                await db.messages.insert_one(ai_msg_dict)

                # If AI determined we should book a job
                if ai_result.get("action") == "book_job" and ai_result.get("booking_data"):
                    try:
                        booking_data = ai_result["booking_data"]

                        # Validate booking data has required fields
                        if not booking_data.get("date") or not booking_data.get("time_slot"):
                            logger.warning(f"Incomplete booking data: {booking_data}")
                        else:
                            # Parse the booking date and time slot
                            tenant_tz = pytz.timezone(tenant.get("timezone", "America/New_York"))
                            booking_date = datetime.strptime(booking_data["date"], "%Y-%m-%d")

                            time_slots = {
                                "morning": (8, 12),
                                "afternoon": (12, 16),
                                "evening": (16, 19)
                            }
                            slot = time_slots.get(booking_data.get("time_slot", "morning"), (8, 12))

                            window_start = tenant_tz.localize(datetime(
                                booking_date.year, booking_date.month, booking_date.day,
                                slot[0], 0, 0
                            ))
                            window_end = tenant_tz.localize(datetime(
                                booking_date.year, booking_date.month, booking_date.day,
                                slot[1], 0, 0
                            ))

                            # Get property from context
                            property_id = booking_context.get("property_id")
                            lead_id = conv.get("ai_booking_lead_id")

                            # Determine job type and calculate quote
                            job_type_str = booking_data.get("job_type", "DIAGNOSTIC").upper()
                            if job_type_str not in ["DIAGNOSTIC", "REPAIR", "MAINTENANCE", "INSTALL"]:
                                job_type_str = "DIAGNOSTIC"

                            urgency = booking_context.get("urgency", "ROUTINE")
                            quote_amount = calculate_quote_amount(job_type_str, urgency)

                            # Create the job
                            job = Job(
                                tenant_id=tenant_id,
                                customer_id=customer["id"],
                                property_id=property_id,
                                lead_id=lead_id,
                                job_type=JobType(job_type_str),
                                priority=JobPriority.NORMAL,
                                service_window_start=window_start,
                                service_window_end=window_end,
                                status=JobStatus.BOOKED,
                                created_by=JobCreatedBy.AI,
                                quote_amount=quote_amount
                            )

                            job_dict = job.model_dump(mode='json')
                            await db.jobs.insert_one(job_dict)

                            # Create quote
                            quote = Quote(
                                tenant_id=tenant_id,
                                customer_id=customer["id"],
                                property_id=property_id,
                                job_id=job.id,
                                amount=quote_amount,
                                description=f"{job_type_str} - {booking_context.get('issue_description', 'Service')}",
                                status=QuoteStatus.SENT
                            )
                            quote_dict = quote.model_dump(mode='json')
                            quote_dict["sent_at"] = datetime.now(timezone.utc).isoformat()
                            await db.quotes.insert_one(quote_dict)

                            # Link quote to job
                            await db.jobs.update_one({"id": job.id}, {"$set": {"quote_id": quote.id}})

                            # Update lead status
                            if lead_id:
                                await db.leads.update_one(
                                    {"id": lead_id},
                                    {"$set": {"status": LeadStatus.JOB_BOOKED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
                                )

                            # Send quote SMS
                            quote_msg = f"Your service quote for {job_type_str} is ${quote_amount:.2f}. Pay securely here: [YOUR PAYMENT LINK HERE]. Reply with any questions!"

                            await twilio_service.send_sms(
                                to_phone=from_phone,
                                body=quote_msg,
                                from_phone=tenant["twilio_phone_number"]
                            )

                            # Log quote SMS
                            quote_sms_msg = Message(
                                tenant_id=tenant_id,
                                conversation_id=conv["id"],
                                customer_id=customer["id"],
                                direction=MessageDirection.OUTBOUND,
                                sender_type=SenderType.SYSTEM,
                                channel=PreferredChannel.SMS,
                                content=quote_msg,
                                metadata={"quote_id": quote.id, "job_id": job.id}
                            )
                            quote_sms_dict = quote_sms_msg.model_dump(mode='json')
                            await db.messages.insert_one(quote_sms_dict)

                            # Mark AI booking as complete
                            await db.conversations.update_one(
                                {"id": conv["id"]},
                                {"$set": {
                                    "ai_booking_active": False,
                                    "ai_booking_completed": True,
                                    "ai_booking_job_id": job.id,
                                    "updated_at": datetime.now(timezone.utc).isoformat()
                                }}
                            )

                            logger.info(f"AI booking completed: Job {job.id} created for customer {customer['id']}")
                    except Exception as booking_err:
                        logger.error(f"Error processing booking data: {booking_err}")

                # Update conversation timestamp
                await db.conversations.update_one(
                    {"id": conv["id"]},
                    {"$set": {
                        "last_message_from": SenderType.AI.value,
                        "last_message_at": datetime.now(timezone.utc).isoformat()
                    }}
                )

            return {"status": "received", "ai_booking": True}

        except Exception as e:
            import traceback
            logger.error(f"Error in AI booking conversation: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fall through to regular AI handling

    # Regular AI response (non-booking conversations)
    try:
        from services.openai_service import openai_service

        # Get conversation history
        history = await db.messages.find(
            {"conversation_id": conv["id"]}, {"_id": 0}
        ).sort("created_at", -1).limit(10).to_list(10)
        history.reverse()

        ai_response = await openai_service.generate_sms_reply(
            tenant_name=tenant["name"],
            tenant_timezone=tenant.get("timezone", "America/New_York"),
            tone_profile=tenant.get("tone_profile", "PROFESSIONAL"),
            customer_name=customer.get("first_name", "there"),
            conversation_history=history,
            current_message=body,
            context_type="GENERAL"
        )

        # Send AI response
        if tenant.get("twilio_phone_number"):
            from services.twilio_service import twilio_service

            result = await twilio_service.send_sms(
                to_phone=from_phone,
                body=ai_response,
                from_phone=tenant["twilio_phone_number"]
            )

            if result["success"]:
                # Log AI response
                ai_msg = Message(
                    tenant_id=tenant_id,
                    conversation_id=conv["id"],
                    customer_id=customer["id"],
                    direction=MessageDirection.OUTBOUND,
                    sender_type=SenderType.AI,
                    channel=PreferredChannel.SMS,
                    content=ai_response,
                    metadata={"twilio_sid": result.get("provider_message_id")}
                )
                ai_msg_dict = ai_msg.model_dump(mode='json')
                await db.messages.insert_one(ai_msg_dict)

                # Update conversation
                await db.conversations.update_one(
                    {"id": conv["id"]},
                    {"$set": {
                        "last_message_from": SenderType.AI.value,
                        "last_message_at": datetime.now(timezone.utc).isoformat()
                    }}
                )

    except Exception as e:
        logger.error(f"Error generating AI response: {e}")

    return {"status": "received"}
