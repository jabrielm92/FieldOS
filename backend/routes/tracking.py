"""Public tracking routes - no auth required"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import logging

from core.database import db
from core.utils import serialize_doc

router = APIRouter(prefix="/track", tags=["tracking"])
logger = logging.getLogger(__name__)


@router.get("/{token}")
async def get_tracking_info(token: str):
    """Get technician tracking info for customer (public, no auth)"""
    job = await db.jobs.find_one({"tracking_token": token}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Tracking link not found or expired")

    tenant = await db.tenants.find_one({"id": job["tenant_id"]}, {"_id": 0})
    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0}) if job.get("property_id") else None

    tech = None
    if job.get("assigned_technician_id"):
        tech_doc = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0})
        if tech_doc:
            tech = {
                "name": tech_doc.get("name"),
                "photo_url": tech_doc.get("photo_url"),
                "vehicle_info": tech_doc.get("vehicle_info"),
            }

    # Calculate minutes remaining
    minutes_remaining = None
    if job.get("estimated_arrival"):
        try:
            eta = datetime.fromisoformat(job["estimated_arrival"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = (eta - now).total_seconds() / 60
            minutes_remaining = max(0, int(diff))
        except Exception:
            pass

    return {
        "status": job.get("status"),
        "job_type": job.get("job_type"),
        "service_window_start": job.get("service_window_start"),
        "service_window_end": job.get("service_window_end"),
        "en_route_at": job.get("en_route_at"),
        "estimated_arrival": job.get("estimated_arrival"),
        "actual_arrival": job.get("actual_arrival"),
        "minutes_remaining": minutes_remaining,
        "technician": tech,
        "company": {
            "name": tenant.get("name") if tenant else None,
            "phone": tenant.get("primary_phone") if tenant else None,
            "logo_url": (tenant.get("branding") or {}).get("logo_url") if tenant else None,
        },
        "property_address": (
            f"{prop.get('address_line1', '')}, {prop.get('city', '')}, {prop.get('state', '')}"
            if prop else None
        ),
        "customer_first_name": customer.get("first_name") if customer else None,
    }
