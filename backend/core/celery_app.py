"""
Celery application configuration for FieldOS background task processing.

Replaces APScheduler for production-grade job queuing with:
- Retry logic and dead-letter queues
- Task monitoring and introspection
- Distributed worker support
- Priority queues

Usage:
    # Start workers:
    celery -A core.celery_app worker --loglevel=info -Q default,reminders,campaigns

    # Start beat scheduler (replaces APScheduler cron):
    celery -A core.celery_app beat --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab
from core.config import REDIS_URL

# ---------------------------------------------------------------------------
# App definition
# ---------------------------------------------------------------------------

celery_app = Celery(
    "fieldos",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.reminders",
        "tasks.campaigns",
        "tasks.reviews",
        "tasks.payments",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Result backend
    result_expires=3600,  # Results kept for 1 hour
    # Retry policy defaults
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Queues
    task_default_queue="default",
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "reminders": {"exchange": "reminders", "routing_key": "reminders"},
        "campaigns": {"exchange": "campaigns", "routing_key": "campaigns"},
        "reviews": {"exchange": "reviews", "routing_key": "reviews"},
        "payments": {"exchange": "payments", "routing_key": "payments"},
    },
    # Beat schedule - replaces APScheduler cron jobs
    beat_schedule={
        # Check for day-before appointment reminders every hour
        "appointment-reminders-day-before": {
            "task": "tasks.reminders.send_day_before_reminders",
            "schedule": crontab(minute=0, hour="*"),
            "options": {"queue": "reminders"},
        },
        # Check for morning-of reminders at 7am UTC daily
        "appointment-reminders-morning": {
            "task": "tasks.reminders.send_morning_reminders",
            "schedule": crontab(minute=0, hour=7),
            "options": {"queue": "reminders"},
        },
        # Check for overdue invoices and send payment reminders daily at 9am UTC
        "payment-reminders": {
            "task": "tasks.payments.send_payment_reminders",
            "schedule": crontab(minute=0, hour=9),
            "options": {"queue": "payments"},
        },
        # Process pending campaign batches every 5 minutes
        "campaign-processing": {
            "task": "tasks.campaigns.process_pending_campaigns",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "campaigns"},
        },
        # Auto review requests - check for eligible completed jobs every 30 minutes
        "review-requests": {
            "task": "tasks.reviews.send_auto_review_requests",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "reviews"},
        },
    },
)
