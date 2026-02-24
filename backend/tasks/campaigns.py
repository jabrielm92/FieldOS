"""Celery tasks: campaign batch processing"""
import asyncio
import logging
from datetime import datetime, timezone

from core.celery_app import celery_app
from core.database import db

logger = logging.getLogger(__name__)


async def _process_campaigns():
    campaigns = await db.campaigns.find({"status": "RUNNING"}).to_list(100)
    for campaign in campaigns:
        try:
            tenant = await db.tenants.find_one({"id": campaign["tenant_id"]})
            if not tenant:
                continue

            recipients = await db.campaign_recipients.find({
                "campaign_id": campaign["id"],
                "status": "PENDING",
            }).limit(10).to_list(10)

            for recipient in recipients:
                customer = await db.customers.find_one({"id": recipient["customer_id"]})
                if not customer:
                    continue

                message = campaign.get("message_template", "")
                message = message.replace("{first_name}", customer.get("first_name", "there"))
                message = message.replace("{last_name}", customer.get("last_name", ""))
                if not message:
                    continue

                from services.twilio_service import twilio_service
                result = await twilio_service.send_sms(
                    to_phone=customer["phone"],
                    body=message,
                    from_phone=tenant.get("twilio_phone_number"),
                )

                status = "SENT" if result.get("success") else "FAILED"
                await db.campaign_recipients.update_one(
                    {"id": recipient["id"]},
                    {"$set": {
                        "status": status,
                        "last_message_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )

        except Exception as exc:
            logger.error(f"Campaign processing error for campaign {campaign.get('id')}: {exc}")


@celery_app.task(
    name="tasks.campaigns.process_pending_campaigns",
    queue="campaigns",
    max_retries=2,
    default_retry_delay=60,
)
def process_pending_campaigns():
    asyncio.run(_process_campaigns())
