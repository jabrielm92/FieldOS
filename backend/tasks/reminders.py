"""
Celery tasks: appointment reminder SMS (day-before and morning-of).
Replaces APScheduler-based reminders from scheduler.py.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from core.celery_app import celery_app
from core.database import db

logger = logging.getLogger(__name__)


async def _send_reminder_sms(tenant: dict, customer: dict, job: dict, reminder_type: str) -> bool:
    from services.twilio_service import twilio_service
    if not twilio_service.is_configured():
        logger.warning("Twilio not configured - skipping reminder")
        return False

    start_time = datetime.fromisoformat(job["service_window_start"].replace("Z", "+00:00"))
    date_str = start_time.strftime("%A, %B %d")
    time_str = start_time.strftime("%I:%M %p")

    if reminder_type == "day_before":
        msg = (
            f"Hi {customer['first_name']}, this is a reminder that your "
            f"{job['job_type'].lower()} appointment with {tenant['name']} is tomorrow, "
            f"{date_str}. We'll arrive around {time_str}. Reply STOP to opt out."
        )
    else:
        msg = (
            f"Good morning {customer['first_name']}! Your {tenant['name']} appointment "
            f"is today around {time_str}. We'll text you when your tech is on the way."
        )

    if tenant.get("sms_signature"):
        msg += f" {tenant['sms_signature']}"

    result = await twilio_service.send_sms(
        to_phone=customer["phone"],
        body=msg,
        from_phone=tenant.get("twilio_phone_number"),
    )
    return result.get("success", False)


async def _process_day_before():
    now = datetime.now(timezone.utc)
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow_start + timedelta(days=1)

    jobs = await db.jobs.find({
        "status": "BOOKED",
        "reminder_day_before_sent": False,
        "service_window_start": {
            "$gte": tomorrow_start.isoformat(),
            "$lt": tomorrow_end.isoformat(),
        },
    }).to_list(200)

    logger.info(f"Day-before reminders: found {len(jobs)} jobs")

    for job in jobs:
        try:
            tenant = await db.tenants.find_one({"id": job["tenant_id"]})
            customer = await db.customers.find_one({"id": job["customer_id"]})
            if not tenant or not customer:
                continue

            success = await _send_reminder_sms(tenant, customer, job, "day_before")
            if success:
                await db.jobs.update_one(
                    {"id": job["id"]},
                    {"$set": {"reminder_day_before_sent": True}},
                )
                logger.info(f"Day-before reminder sent: job={job['id']}")
        except Exception as exc:
            logger.error(f"Day-before reminder failed for job {job.get('id')}: {exc}")


async def _process_morning():
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    jobs = await db.jobs.find({
        "status": "BOOKED",
        "reminder_morning_of_sent": False,
        "service_window_start": {
            "$gte": today_start.isoformat(),
            "$lt": today_end.isoformat(),
        },
    }).to_list(200)

    logger.info(f"Morning reminders: found {len(jobs)} jobs")

    for job in jobs:
        try:
            tenant = await db.tenants.find_one({"id": job["tenant_id"]})
            customer = await db.customers.find_one({"id": job["customer_id"]})
            if not tenant or not customer:
                continue

            success = await _send_reminder_sms(tenant, customer, job, "morning_of")
            if success:
                await db.jobs.update_one(
                    {"id": job["id"]},
                    {"$set": {"reminder_morning_of_sent": True}},
                )
        except Exception as exc:
            logger.error(f"Morning reminder failed for job {job.get('id')}: {exc}")


@celery_app.task(
    name="tasks.reminders.send_day_before_reminders",
    queue="reminders",
    max_retries=3,
    default_retry_delay=300,
)
def send_day_before_reminders():
    asyncio.run(_process_day_before())


@celery_app.task(
    name="tasks.reminders.send_morning_reminders",
    queue="reminders",
    max_retries=3,
    default_retry_delay=300,
)
def send_morning_reminders():
    asyncio.run(_process_morning())
