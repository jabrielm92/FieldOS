"""
Background Job Scheduler - Handles automated reminders and campaign processing
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from motor.motor_asyncio import AsyncIOMotorClient
import os

logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'test_database')


async def get_db():
    """Get database connection"""
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name], client


async def send_reminder_sms(tenant, customer, job, reminder_type):
    """Send reminder SMS to customer"""
    from services.twilio_service import twilio_service
    
    if not twilio_service.is_configured():
        logger.warning("Twilio not configured - skipping reminder")
        return False
    
    # Format the date/time
    start_time = datetime.fromisoformat(job['service_window_start'].replace('Z', '+00:00'))
    date_str = start_time.strftime("%A, %B %d")
    time_str = f"{start_time.strftime('%I:%M %p')}"
    
    # Build message based on reminder type
    if reminder_type == "day_before":
        message = f"Hi {customer['first_name']}, this is a reminder that your {job['job_type'].lower()} appointment with {tenant['name']} is tomorrow, {date_str}. We'll arrive between {time_str}. Reply STOP to opt out."
    else:  # morning_of
        message = f"Good morning {customer['first_name']}! Your {tenant['name']} technician will arrive today between {time_str}. We'll text you when they're on the way."
    
    # Add signature if configured
    if tenant.get('sms_signature'):
        message += f" {tenant['sms_signature']}"
    
    result = await twilio_service.send_sms(
        to_phone=customer['phone'],
        body=message
    )
    
    return result.get('success', False)


async def process_day_before_reminders():
    """Send reminders for jobs scheduled tomorrow"""
    logger.info("Processing day-before reminders...")
    
    db, client = await get_db()
    
    try:
        # Get tomorrow's date range
        now = datetime.now(timezone.utc)
        tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        
        # Find jobs that need day-before reminder
        jobs = await db.jobs.find({
            "status": "BOOKED",
            "reminder_day_before_sent": False,
            "service_window_start": {
                "$gte": tomorrow_start.isoformat(),
                "$lt": tomorrow_end.isoformat()
            }
        }).to_list(100)
        
        logger.info(f"Found {len(jobs)} jobs needing day-before reminders")
        
        for job in jobs:
            try:
                # Get tenant and customer
                tenant = await db.tenants.find_one({"id": job['tenant_id']})
                customer = await db.customers.find_one({"id": job['customer_id']})
                
                if not tenant or not customer:
                    continue
                
                # Send reminder
                success = await send_reminder_sms(tenant, customer, job, "day_before")
                
                if success:
                    # Update job flag
                    await db.jobs.update_one(
                        {"id": job['id']},
                        {"$set": {"reminder_day_before_sent": True}}
                    )
                    logger.info(f"Day-before reminder sent for job {job['id']}")
                    
                    # Log the message
                    from models import Message, MessageDirection, SenderType, PreferredChannel
                    msg = {
                        "id": str(__import__('uuid').uuid4()),
                        "tenant_id": job['tenant_id'],
                        "conversation_id": "",
                        "customer_id": job['customer_id'],
                        "direction": "OUTBOUND",
                        "sender_type": "SYSTEM",
                        "channel": "SMS",
                        "content": f"[Auto] Day-before reminder sent for {job['job_type']} appointment",
                        "is_call_summary": False,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    await db.messages.insert_one(msg)
                    
            except Exception as e:
                logger.error(f"Error sending reminder for job {job['id']}: {e}")
                
    finally:
        client.close()


async def process_morning_reminders():
    """Send morning-of reminders for today's jobs"""
    logger.info("Processing morning-of reminders...")
    
    db, client = await get_db()
    
    try:
        # Get today's date range
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Find jobs that need morning reminder
        jobs = await db.jobs.find({
            "status": "BOOKED",
            "reminder_morning_of_sent": False,
            "service_window_start": {
                "$gte": today_start.isoformat(),
                "$lt": today_end.isoformat()
            }
        }).to_list(100)
        
        logger.info(f"Found {len(jobs)} jobs needing morning reminders")
        
        for job in jobs:
            try:
                tenant = await db.tenants.find_one({"id": job['tenant_id']})
                customer = await db.customers.find_one({"id": job['customer_id']})
                
                if not tenant or not customer:
                    continue
                
                success = await send_reminder_sms(tenant, customer, job, "morning_of")
                
                if success:
                    await db.jobs.update_one(
                        {"id": job['id']},
                        {"$set": {"reminder_morning_of_sent": True}}
                    )
                    logger.info(f"Morning reminder sent for job {job['id']}")
                    
            except Exception as e:
                logger.error(f"Error sending morning reminder for job {job['id']}: {e}")
                
    finally:
        client.close()


async def process_campaigns():
    """Process running campaigns and send messages"""
    logger.info("Processing campaigns...")
    
    db, client = await get_db()
    
    try:
        # Find running campaigns
        campaigns = await db.campaigns.find({"status": "RUNNING"}).to_list(100)
        
        for campaign in campaigns:
            try:
                tenant = await db.tenants.find_one({"id": campaign['tenant_id']})
                if not tenant:
                    continue
                
                # Get pending recipients
                recipients = await db.campaign_recipients.find({
                    "campaign_id": campaign['id'],
                    "status": "PENDING"
                }).limit(10).to_list(10)  # Process 10 at a time
                
                for recipient in recipients:
                    customer = await db.customers.find_one({"id": recipient['customer_id']})
                    if not customer:
                        continue
                    
                    # Build message from template
                    message = campaign.get('message_template', '')
                    message = message.replace('{first_name}', customer.get('first_name', 'there'))
                    message = message.replace('{last_name}', customer.get('last_name', ''))
                    
                    if not message:
                        continue
                    
                    from services.twilio_service import twilio_service
                    result = await twilio_service.send_sms(
                        to_phone=customer['phone'],
                        body=message
                    )
                    
                    if result.get('success'):
                        await db.campaign_recipients.update_one(
                            {"id": recipient['id']},
                            {"$set": {
                                "status": "SENT",
                                "last_message_at": datetime.now(timezone.utc).isoformat()
                            }}
                        )
                        
            except Exception as e:
                logger.error(f"Error processing campaign {campaign['id']}: {e}")
                
    finally:
        client.close()


# Scheduler instance
scheduler = AsyncIOScheduler()


def init_scheduler():
    """Initialize the background job scheduler"""
    # Day-before reminders - run at 4 PM daily
    scheduler.add_job(
        process_day_before_reminders,
        CronTrigger(hour=16, minute=0),
        id='day_before_reminders',
        replace_existing=True
    )
    
    # Morning reminders - run at 7 AM daily
    scheduler.add_job(
        process_morning_reminders,
        CronTrigger(hour=7, minute=0),
        id='morning_reminders',
        replace_existing=True
    )
    
    # Campaign processing - run every hour
    scheduler.add_job(
        process_campaigns,
        IntervalTrigger(hours=1),
        id='campaign_processor',
        replace_existing=True
    )
    
    # Also run reminders check every 30 minutes for testing
    scheduler.add_job(
        process_day_before_reminders,
        IntervalTrigger(minutes=30),
        id='day_before_reminders_interval',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Background scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
