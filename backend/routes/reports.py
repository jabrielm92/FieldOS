"""Reports and Analytics routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs
from models import QuoteStatus

router = APIRouter(tags=["reports"])
logger = logging.getLogger(__name__)


@router.get("/reports/summary")
async def get_reports_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get summary report for tenant"""
    # Default to last 30 days
    if not date_from:
        date_from = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = datetime.now(timezone.utc).isoformat()

    # Leads by source
    leads_pipeline = [
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": date_from, "$lte": date_to}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]
    leads_by_source = await db.leads.aggregate(leads_pipeline).to_list(100)

    # Jobs by status
    jobs_pipeline = [
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": date_from, "$lte": date_to}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    jobs_by_status = await db.jobs.aggregate(jobs_pipeline).to_list(100)

    # Quote stats
    total_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": date_from, "$lte": date_to}
    })
    accepted_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "status": QuoteStatus.ACCEPTED.value,
        "created_at": {"$gte": date_from, "$lte": date_to}
    })

    # Total counts
    total_leads = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": date_from, "$lte": date_to}
    })
    total_jobs = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": date_from, "$lte": date_to}
    })

    return {
        "period": {"from": date_from, "to": date_to},
        "leads": {
            "total": total_leads,
            "by_source": {item["_id"]: item["count"] for item in leads_by_source}
        },
        "jobs": {
            "total": total_jobs,
            "by_status": {item["_id"]: item["count"] for item in jobs_by_status}
        },
        "quotes": {
            "total": total_quotes,
            "accepted": accepted_quotes,
            "conversion_rate": round(accepted_quotes / total_quotes * 100, 1) if total_quotes > 0 else 0
        }
    }


@router.get("/analytics/overview")
async def get_analytics_overview(
    period: str = "30d",
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive analytics overview"""
    # Calculate date range
    now = datetime.now(timezone.utc)
    if period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=30)

    start_str = start_date.isoformat()

    # Lead metrics
    total_leads = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_str}
    })

    leads_by_status = await db.leads.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": start_str}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(20)

    leads_by_source = await db.leads.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": start_str}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]).to_list(20)

    # Job metrics
    total_jobs = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_str}
    })

    jobs_by_status = await db.jobs.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": start_str}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(20)

    jobs_by_type = await db.jobs.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": start_str}}},
        {"$group": {"_id": "$job_type", "count": {"$sum": 1}}}
    ]).to_list(20)

    completed_jobs = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "status": "COMPLETED",
        "created_at": {"$gte": start_str}
    })

    # Quote metrics
    total_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_str}
    })

    accepted_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "status": "ACCEPTED",
        "created_at": {"$gte": start_str}
    })

    # Revenue from accepted quotes
    revenue_pipeline = [
        {"$match": {
            "tenant_id": tenant_id,
            "status": "ACCEPTED",
            "created_at": {"$gte": start_str}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    revenue_result = await db.quotes.aggregate(revenue_pipeline).to_list(1)
    quote_revenue = revenue_result[0]["total"] if revenue_result else 0

    # Revenue from jobs (quote_amount field)
    # Potential revenue: booked/scheduled jobs
    potential_jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": {"$in": ["SCHEDULED", "BOOKED", "EN_ROUTE", "ON_SITE"]},
        "created_at": {"$gte": start_str}
    }, {"_id": 0, "quote_amount": 1}).to_list(1000)
    potential_revenue = sum(j.get("quote_amount", 0) or 0 for j in potential_jobs)

    # Completed revenue: completed jobs
    completed_jobs_revenue = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": "COMPLETED",
        "created_at": {"$gte": start_str}
    }, {"_id": 0, "quote_amount": 1}).to_list(1000)
    job_completed_revenue = sum(j.get("quote_amount", 0) or 0 for j in completed_jobs_revenue)

    # Invoiced (paid) revenue
    paid_invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": "PAID",
        "created_at": {"$gte": start_str}
    }, {"_id": 0, "amount": 1}).to_list(1000)
    invoiced_revenue = sum(i.get("amount", 0) or 0 for i in paid_invoices)

    # Total revenue is the higher of invoiced or completed job revenue (to avoid double counting)
    total_revenue = max(invoiced_revenue, job_completed_revenue, quote_revenue)

    # Daily trends (last 14 days)
    daily_trends = []
    for i in range(14):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_leads = await db.leads.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })

        day_jobs = await db.jobs.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })

        daily_trends.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "leads": day_leads,
            "jobs": day_jobs
        })

    daily_trends.reverse()

    # Conversion rates
    leads_converted = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "status": "JOB_BOOKED",
        "created_at": {"$gte": start_str}
    })

    lead_conversion_rate = round(leads_converted / total_leads * 100, 1) if total_leads > 0 else 0
    quote_conversion_rate = round(accepted_quotes / total_quotes * 100, 1) if total_quotes > 0 else 0
    job_completion_rate = round(completed_jobs / total_jobs * 100, 1) if total_jobs > 0 else 0

    # Technician performance
    tech_performance = await db.jobs.aggregate([
        {"$match": {
            "tenant_id": tenant_id,
            "status": "COMPLETED",
            "assigned_technician_id": {"$ne": None},
            "created_at": {"$gte": start_str}
        }},
        {"$group": {
            "_id": "$assigned_technician_id",
            "completed_jobs": {"$sum": 1}
        }}
    ]).to_list(20)

    # Enrich with tech names
    for perf in tech_performance:
        tech = await db.technicians.find_one({"id": perf["_id"]}, {"_id": 0, "name": 1})
        perf["technician_name"] = tech["name"] if tech else "Unknown"

    return {
        "period": period,
        "summary": {
            "total_leads": total_leads,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "total_quotes": total_quotes,
            "accepted_quotes": accepted_quotes,
            "total_revenue": round(total_revenue, 2),
            "potential_revenue": round(potential_revenue, 2),
            "job_completed_revenue": round(job_completed_revenue, 2),
            "invoiced_revenue": round(invoiced_revenue, 2)
        },
        "conversion_rates": {
            "lead_to_job": lead_conversion_rate,
            "quote_acceptance": quote_conversion_rate,
            "job_completion": job_completion_rate
        },
        "leads": {
            "by_status": {item["_id"]: item["count"] for item in leads_by_status},
            "by_source": {item["_id"]: item["count"] for item in leads_by_source}
        },
        "jobs": {
            "by_status": {item["_id"]: item["count"] for item in jobs_by_status},
            "by_type": {item["_id"]: item["count"] for item in jobs_by_type}
        },
        "daily_trends": daily_trends,
        "technician_performance": tech_performance
    }


@router.get("/reports/revenue")
async def get_revenue_report(
    start_date: str = None,
    end_date: str = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get revenue report with payment tracking"""
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d')

    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_date, "$lte": end_date + "T23:59:59"}
    }, {"_id": 0}).to_list(10000)

    total_invoiced = sum(float(inv.get('total', 0)) for inv in invoices)
    total_paid = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') == 'PAID')
    total_outstanding = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') in ['SENT', 'PENDING'])
    total_overdue = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') == 'OVERDUE')

    jobs = await db.jobs.find({"tenant_id": tenant_id, "created_at": {"$gte": start_date}}, {"_id": 0}).to_list(10000)
    revenue_by_type = {}
    for job in jobs:
        jtype = job.get('job_type', 'OTHER')
        revenue_by_type[jtype] = revenue_by_type.get(jtype, 0) + float(job.get('quoted_amount', 0))

    daily_revenue = {}
    for inv in invoices:
        if inv.get('status') == 'PAID' and inv.get('paid_at'):
            day = inv['paid_at'][:10]
            daily_revenue[day] = daily_revenue.get(day, 0) + float(inv.get('total', 0))

    return {
        "period": {"start": start_date, "end": end_date},
        "summary": {
            "total_invoiced": round(total_invoiced, 2),
            "total_paid": round(total_paid, 2),
            "total_outstanding": round(total_outstanding, 2),
            "total_overdue": round(total_overdue, 2),
            "collection_rate": round(total_paid / total_invoiced * 100, 1) if total_invoiced > 0 else 0
        },
        "invoices_count": {
            "total": len(invoices),
            "paid": len([i for i in invoices if i.get('status') == 'PAID']),
            "outstanding": len([i for i in invoices if i.get('status') in ['SENT', 'PENDING']]),
            "overdue": len([i for i in invoices if i.get('status') == 'OVERDUE'])
        },
        "revenue_by_job_type": revenue_by_type,
        "daily_revenue": dict(sorted(daily_revenue.items()))
    }
