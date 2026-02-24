"""Celery tasks: payment reminder SMS for overdue invoices"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from core.celery_app import celery_app
from core.database import db

logger = logging.getLogger(__name__)


async def _send_payment_reminders():
    tenants = await db.tenants.find({"auto_payment_reminder_days": {"$gt": 0}}).to_list(1000)

    for tenant in tenants:
        days = tenant.get("auto_payment_reminder_days", 7)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        invoices = await db.invoices.find({
            "tenant_id": tenant["id"],
            "status": {"$in": ["SENT", "PENDING", "OVERDUE"]},
            "due_date": {"$lte": cutoff},
            "payment_reminder_sent_at": {"$exists": False},
        }).to_list(50)

        for invoice in invoices:
            try:
                customer = await db.customers.find_one({"id": invoice["customer_id"]})
                if not customer or not customer.get("phone"):
                    continue

                total = invoice.get("total", 0)
                message = (
                    f"Hi {customer.get('first_name', 'there')}, friendly reminder that "
                    f"your invoice from {tenant['name']} for ${total:.2f} is past due."
                )
                if invoice.get("stripe_payment_link"):
                    message += f" Pay securely: {invoice['stripe_payment_link']}"
                if tenant.get("sms_signature"):
                    message += f" {tenant['sms_signature']}"

                from services.twilio_service import twilio_service
                if tenant.get("twilio_phone_number"):
                    await twilio_service.send_sms(
                        to_phone=customer["phone"],
                        body=message,
                        from_phone=tenant["twilio_phone_number"],
                    )
                    await db.invoices.update_one(
                        {"id": invoice["id"]},
                        {"$set": {
                            "status": "OVERDUE",
                            "payment_reminder_sent_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
                    logger.info(f"Payment reminder sent for invoice {invoice['id']}")
            except Exception as exc:
                logger.error(f"Payment reminder error for invoice {invoice.get('id')}: {exc}")


@celery_app.task(
    name="tasks.payments.send_payment_reminders",
    queue="payments",
    max_retries=2,
    default_retry_delay=300,
)
def send_payment_reminders():
    asyncio.run(_send_payment_reminders())
