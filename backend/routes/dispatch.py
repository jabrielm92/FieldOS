"""Dispatch board routes - job assignment and daily operations view"""
import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs

router = APIRouter(prefix="/dispatch", tags=["dispatch"])
logger = logging.getLogger(__name__)


@router.get("/board")
async def get_dispatch_board(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Get dispatch board data — jobs and technicians for a given day"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except Exception:
        tenant_tz = pytz.timezone("America/New_York")

    if not date:
        date = datetime.now(tenant_tz).strftime("%Y-%m-%d")

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        date_start = tenant_tz.localize(target_date.replace(hour=0, minute=0, second=0))
        date_end = date_start + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "service_window_start": {
            "$gte": date_start.isoformat(),
            "$lt": date_end.isoformat(),
        },
        "status": {"$nin": ["CANCELLED"]},
    }, {"_id": 0}).to_list(100)

    for job in jobs:
        customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
        prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
        job["customer"] = serialize_doc(customer) if customer else None
        job["property"] = serialize_doc(prop) if prop else None

    technicians = await db.technicians.find(
        {"tenant_id": tenant_id, "active": True}, {"_id": 0}
    ).to_list(50)

    unassigned_jobs = []
    assigned_by_tech: dict = {}

    for job in jobs:
        tech_id = job.get("assigned_technician_id")
        if tech_id:
            assigned_by_tech.setdefault(tech_id, []).append(serialize_doc(job))
        else:
            unassigned_jobs.append(serialize_doc(job))

    technicians_with_jobs = []
    for tech in technicians:
        tech_data = serialize_doc(tech)
        tech_data["jobs"] = assigned_by_tech.get(tech["id"], [])
        technicians_with_jobs.append(tech_data)

    return {
        "date": date,
        "technicians": technicians_with_jobs,
        "unassigned_jobs": unassigned_jobs,
        "summary": {
            "total_jobs": len(jobs),
            "unassigned": len(unassigned_jobs),
            "assigned": len(jobs) - len(unassigned_jobs),
        },
    }


@router.post("/assign")
async def assign_job_to_tech(
    job_id: str,
    technician_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Assign or unassign a job to a technician"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if technician_id:
        tech = await db.technicians.find_one({"id": technician_id, "tenant_id": tenant_id})
        if not tech:
            raise HTTPException(status_code=404, detail="Technician not found")

    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "assigned_technician_id": technician_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    return {"success": True, "job_id": job_id, "technician_id": technician_id}
