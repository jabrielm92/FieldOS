"""Celery tasks: auto review request SMS after job completion"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from core.celery_app import celery_app
from core.database import db

logger = logging.getLogger(__name__)


async def _send_auto_reviews():
    tenants = await db.tenants.find({"auto_review_request_days": {"$gt": 0}}).to_list(1000)

    for tenant in tenants:
        days = tenant.get("auto_review_request_days", 3)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        jobs = await db.jobs.find({
            "tenant_id": tenant["id"],
            "status": "COMPLETED",
            "completed_at": {"$lte": cutoff},
            "review_requested_at": {"$exists": False},
        }).to_list(50)

        for job in jobs:
            try:
                customer = await db.customers.find_one({"id": job["customer_id"]})
                if not customer or not customer.get("phone"):
                    continue

                branding = tenant.get("branding", {})
                review_url = (
                    branding.get("google_review_url")
                    or branding.get("yelp_review_url")
                    or ""
                )

                message = (
                    f"Hi {customer.get('first_name', 'there')}! "
                    f"Thank you for choosing {tenant['name']}. "
                    f"We hope you're happy with our service!"
                )
                if review_url:
                    message += f" We'd love your feedback: {review_url}"
                if tenant.get("sms_signature"):
                    message += f" {tenant['sms_signature']}"

                from services.twilio_service import twilio_service
                if tenant.get("twilio_phone_number"):
                    await twilio_service.send_sms(
                        to_phone=customer["phone"],
                        body=message,
                        from_phone=tenant["twilio_phone_number"],
                    )
                    await db.jobs.update_one(
                        {"id": job["id"]},
                        {"$set": {"review_requested_at": datetime.now(timezone.utc).isoformat()}},
                    )
                    logger.info(f"Auto review request sent for job {job['id']}")
            except Exception as exc:
                logger.error(f"Auto review error for job {job.get('id')}: {exc}")


@celery_app.task(
    name="tasks.reviews.send_auto_review_requests",
    queue="reviews",
    max_retries=2,
    default_retry_delay=120,
)
def send_auto_review_requests():
    asyncio.run(_send_auto_reviews())
