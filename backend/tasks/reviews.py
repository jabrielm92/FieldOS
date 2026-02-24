"""Celery tasks: auto review request SMS after job completion"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from core.celery_app import celery_app
from core.database import db

logger = logging.getLogger(__name__)


async def _send_auto_reviews():
    """
    Process pending review requests:
    - Honors per-tenant review_settings (enabled, delay_hours)
    - Skips customers with review_opt_out=True
    - Enforces 30-day cooldown between requests per customer
    - Uses review_scheduled_at if set by /complete endpoint
    """
    now = datetime.now(timezone.utc)

    # Find all completed jobs with a review scheduled but not yet sent
    # Either has review_scheduled_at in the past, or uses legacy auto_review_request_days
    jobs_cursor = db.jobs.find({
        "status": "COMPLETED",
        "review_request_sent": {"$ne": True},
        "$or": [
            {"review_scheduled_at": {"$lte": now.isoformat()}},
            {"review_scheduled_at": {"$exists": False}, "completed_at": {"$exists": True}},
        ]
    })
    jobs = await jobs_cursor.to_list(200)

    for job in jobs:
        try:
            tenant = await db.tenants.find_one({"id": job["tenant_id"]})
            if not tenant:
                continue

            review_settings = tenant.get("review_settings") or {}
            # Skip if reviews disabled for tenant
            if review_settings.get("enabled") is False:
                continue

            delay_hours = review_settings.get("delay_hours", 2)

            # For jobs without review_scheduled_at, check legacy delay
            if not job.get("review_scheduled_at"):
                # Fall back to auto_review_request_days (days after completion)
                legacy_days = tenant.get("auto_review_request_days", 0)
                if not legacy_days:
                    continue
                if not job.get("completed_at"):
                    continue
                cutoff = (now - timedelta(days=legacy_days)).isoformat()
                if job["completed_at"] > cutoff:
                    continue  # Not ready yet

            customer = await db.customers.find_one({"id": job["customer_id"]})
            if not customer or not customer.get("phone"):
                continue

            # Skip if customer opted out
            if customer.get("review_opt_out"):
                logger.info(f"Skipping review for opted-out customer {customer['id']}")
                continue

            # 30-day cooldown per customer
            last_requested = customer.get("last_review_requested_at")
            if last_requested:
                last_dt = datetime.fromisoformat(last_requested.replace("Z", "+00:00"))
                if (now - last_dt).days < 30:
                    logger.info(f"Skipping review for customer {customer['id']} — 30-day cooldown")
                    continue

            # Build review URL
            review_urls = {
                "google": review_settings.get("google_review_url", ""),
                "yelp": review_settings.get("yelp_review_url", ""),
                "facebook": review_settings.get("facebook_review_url", ""),
            }
            preferred = review_settings.get("preferred_platform", "google")
            review_url = review_urls.get(preferred) or next((v for v in review_urls.values() if v), "")

            # Build message from template or default
            template = review_settings.get("message_template", "")
            if template:
                message = (
                    template
                    .replace("{first_name}", customer.get("first_name", "there"))
                    .replace("{company_name}", tenant.get("name", "us"))
                    .replace("{review_link}", review_url)
                )
            else:
                message = (
                    f"Hi {customer.get('first_name', 'there')}! "
                    f"Thank you for choosing {tenant['name']}. "
                    f"We hope you're happy with our service!"
                )
                if review_url:
                    message += f" We'd love your feedback: {review_url}"
                if tenant.get("sms_signature"):
                    message += f" {tenant['sms_signature']}"

            if not tenant.get("twilio_phone_number"):
                continue

            from services.twilio_service import twilio_service
            result = await twilio_service.send_sms(
                to_phone=customer["phone"],
                body=message,
                from_phone=tenant["twilio_phone_number"],
            )

            if result.get("success"):
                sent_at = now.isoformat()
                await db.jobs.update_one(
                    {"id": job["id"]},
                    {"$set": {
                        "review_requested_at": sent_at,
                        "review_request_sent": True,
                        "review_platform": preferred,
                    }},
                )
                await db.customers.update_one(
                    {"id": customer["id"]},
                    {
                        "$set": {"last_review_requested_at": sent_at},
                        "$inc": {"review_request_count": 1},
                    }
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
