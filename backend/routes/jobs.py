"""Jobs routes with On My Way and Review Request features"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging

router = APIRouter(tags=["jobs"])
logger = logging.getLogger(__name__)

# Injected dependencies
db = None
get_tenant_id = None
get_current_user = None
serialize_doc = None

def init_jobs_routes(_db, _get_tenant_id, _get_current_user, _serialize_doc):
    global db, get_tenant_id, get_current_user, serialize_doc
    db = _db
    get_tenant_id = _get_tenant_id
    get_current_user = _get_current_user
    serialize_doc = _serialize_doc


class OnMyWayRequest(BaseModel):
    eta_minutes: int = 30
    custom_message: Optional[str] = None


class ReviewRequestPayload(BaseModel):
    job_id: str
    platform: str = "google"  # google, yelp, facebook


@router.post("/jobs/{job_id}/on-my-way")
async def send_on_my_way(
    job_id: str,
    data: OnMyWayRequest,
    tenant_id: str = Depends(lambda: get_tenant_id),
    current_user: dict = Depends(lambda: get_current_user)
):
    """Send 'On My Way' SMS to customer with ETA"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured for tenant")
    
    technician = await db.technicians.find_one({"id": job.get("technician_id")}, {"_id": 0})
    tech_name = technician.get("name", "Your technician") if technician else "Your technician"
    
    # Build message
    if data.custom_message:
        message = data.custom_message
    else:
        message = f"Hi {customer.get('name', 'there')}! {tech_name} from {tenant['name']} is on the way and will arrive in approximately {data.eta_minutes} minutes."
        if tenant.get("sms_signature"):
            message += f" {tenant['sms_signature']}"
    
    # Send SMS
    try:
        from services.twilio_service import twilio_service
        await twilio_service.send_sms(
            to_phone=customer["phone"],
            message=message,
            from_phone=tenant["twilio_phone_number"]
        )
        
        # Update job status
        await db.jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "EN_ROUTE",
                "en_route_at": datetime.now(timezone.utc).isoformat(),
                "eta_minutes": data.eta_minutes,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"success": True, "message": "On My Way notification sent"}
    except Exception as e:
        logger.error(f"Failed to send On My Way SMS: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")


@router.post("/jobs/{job_id}/request-review")
async def request_review(
    job_id: str,
    data: ReviewRequestPayload,
    tenant_id: str = Depends(lambda: get_tenant_id),
    current_user: dict = Depends(lambda: get_current_user)
):
    """Send review request SMS to customer after job completion"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Job must be completed to request review")
    
    customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured")
    
    # Get review URL from tenant branding or use placeholder
    branding = tenant.get("branding", {})
    review_urls = {
        "google": branding.get("google_review_url", ""),
        "yelp": branding.get("yelp_review_url", ""),
        "facebook": branding.get("facebook_review_url", "")
    }
    
    review_url = review_urls.get(data.platform, "")
    
    # Build message
    message = f"Hi {customer.get('name', 'there')}! Thank you for choosing {tenant['name']}. We hope you're satisfied with our service!"
    if review_url:
        message += f" If you have a moment, we'd really appreciate a review: {review_url}"
    else:
        message += " Your feedback means the world to us."
    
    if tenant.get("sms_signature"):
        message += f" {tenant['sms_signature']}"
    
    # Send SMS
    try:
        from services.twilio_service import twilio_service
        await twilio_service.send_sms(
            to_phone=customer["phone"],
            message=message,
            from_phone=tenant["twilio_phone_number"]
        )
        
        # Mark review requested
        await db.jobs.update_one(
            {"id": job_id},
            {"$set": {
                "review_requested_at": datetime.now(timezone.utc).isoformat(),
                "review_platform": data.platform,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"success": True, "message": "Review request sent"}
    except Exception as e:
        logger.error(f"Failed to send review request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")
