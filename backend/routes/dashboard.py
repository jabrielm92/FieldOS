"""Dashboard route - tenant KPI and metrics overview"""
import pytz
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_docs
from models import QuoteStatus

router = APIRouter(tags=["dashboard"])
logger = logging.getLogger(__name__)


@router.get("/dashboard")
async def get_dashboard(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Get dashboard KPI data for tenant"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except Exception:
        tenant_tz = pytz.timezone("America/New_York")

    now = datetime.now(tenant_tz)
    today_start = tenant_tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = tenant_tz.localize(datetime(now.year, now.month, 1, 0, 0, 0))
    thirty_days_ago = now - timedelta(days=30)

    leads_week = await db.leads.count_documents({
        "tenant_id": tenant_id, "created_at": {"$gte": week_start.isoformat()},
    })
    leads_month = await db.leads.count_documents({
        "tenant_id": tenant_id, "created_at": {"$gte": month_start.isoformat()},
    })
    jobs_week = await db.jobs.count_documents({
        "tenant_id": tenant_id, "created_at": {"$gte": week_start.isoformat()},
    })

    jobs_today = await db.jobs.find({
        "tenant_id": tenant_id,
        "service_window_start": {
            "$gte": today_start.isoformat(),
            "$lt": (today_start + timedelta(days=1)).isoformat(),
        },
    }, {"_id": 0}).to_list(50)

    tomorrow_start = today_start + timedelta(days=1)
    jobs_tomorrow = await db.jobs.find({
        "tenant_id": tenant_id,
        "service_window_start": {
            "$gte": tomorrow_start.isoformat(),
            "$lt": (tomorrow_start + timedelta(days=1)).isoformat(),
        },
    }, {"_id": 0}).to_list(50)

    recent_leads = await db.leads.find(
        {"tenant_id": tenant_id}, {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)

    leads_by_source = await db.leads.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": thirty_days_ago.isoformat()}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
    ]).to_list(20)

    jobs_by_status = await db.jobs.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": thirty_days_ago.isoformat()}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]).to_list(20)

    total_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id, "created_at": {"$gte": month_start.isoformat()},
    })
    accepted_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "status": QuoteStatus.ACCEPTED.value,
        "created_at": {"$gte": month_start.isoformat()},
    })

    potential_jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": {"$in": ["SCHEDULED", "BOOKED", "EN_ROUTE", "ON_SITE"]},
        "created_at": {"$gte": month_start.isoformat()},
    }, {"_id": 0, "quote_amount": 1}).to_list(1000)
    potential_revenue = sum(j.get("quote_amount", 0) or 0 for j in potential_jobs)

    completed_jobs_list = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": "COMPLETED",
        "created_at": {"$gte": month_start.isoformat()},
    }, {"_id": 0, "quote_amount": 1}).to_list(1000)
    completed_revenue = sum(j.get("quote_amount", 0) or 0 for j in completed_jobs_list)

    paid_invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": "PAID",
        "created_at": {"$gte": month_start.isoformat()},
    }, {"_id": 0, "amount": 1}).to_list(1000)
    invoiced_revenue = sum(i.get("amount", 0) or 0 for i in paid_invoices)

    return {
        "metrics": {
            "leads_this_week": leads_week,
            "leads_this_month": leads_month,
            "jobs_this_week": jobs_week,
            "quote_conversion": round(accepted_quotes / total_quotes * 100, 1) if total_quotes > 0 else 0,
            "potential_revenue": round(potential_revenue, 2),
            "completed_revenue": round(completed_revenue, 2),
            "invoiced_revenue": round(invoiced_revenue, 2),
            "total_estimated_revenue": round(potential_revenue + completed_revenue, 2),
        },
        "jobs_today": serialize_docs(jobs_today),
        "jobs_tomorrow": serialize_docs(jobs_tomorrow),
        "recent_leads": serialize_docs(recent_leads),
        "charts": {
            "leads_by_source": {item["_id"]: item["count"] for item in leads_by_source},
            "jobs_by_status": {item["_id"]: item["count"] for item in jobs_by_status},
        },
    }
