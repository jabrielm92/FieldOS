"""
Integrations routes - QuickBooks OAuth and CSV export helpers
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import os
import io
import csv
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs

router = APIRouter(prefix="/integrations", tags=["integrations"])
logger = logging.getLogger(__name__)


# ============= QUICKBOOKS OAUTH =============

QB_CLIENT_ID = os.environ.get("QUICKBOOKS_CLIENT_ID", "")
QB_CLIENT_SECRET = os.environ.get("QUICKBOOKS_CLIENT_SECRET", "")
QB_REDIRECT_URI = os.environ.get("QUICKBOOKS_REDIRECT_URI", "")
QB_ENVIRONMENT = os.environ.get("QUICKBOOKS_ENVIRONMENT", "sandbox")  # sandbox or production

QB_AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
QB_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QB_SCOPE = "com.intuit.quickbooks.accounting"


@router.get("/quickbooks/status")
async def quickbooks_status(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Get QuickBooks connection status for this tenant"""
    qb = await db.quickbooks_connections.find_one({"tenant_id": tenant_id}, {"_id": 0})
    if not qb:
        return {"connected": False}
    return {
        "connected": True,
        "realm_id": qb.get("realm_id"),
        "company_name": qb.get("company_name"),
        "connected_at": qb.get("connected_at"),
        "expires_at": qb.get("expires_at"),
    }


@router.get("/quickbooks/connect")
async def quickbooks_connect(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Initiate QuickBooks OAuth flow"""
    if not QB_CLIENT_ID:
        raise HTTPException(
            status_code=501,
            detail="QuickBooks integration not configured. Set QUICKBOOKS_CLIENT_ID, QUICKBOOKS_CLIENT_SECRET, and QUICKBOOKS_REDIRECT_URI in environment.",
        )
    import urllib.parse
    import secrets
    state = f"{tenant_id}:{secrets.token_urlsafe(16)}"
    params = {
        "client_id": QB_CLIENT_ID,
        "redirect_uri": QB_REDIRECT_URI,
        "response_type": "code",
        "scope": QB_SCOPE,
        "state": state,
    }
    auth_url = f"{QB_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/quickbooks/callback")
async def quickbooks_callback(
    code: str,
    state: str,
    realmId: Optional[str] = None,
    request: Request = None,
):
    """Handle QuickBooks OAuth callback and store tokens"""
    if not QB_CLIENT_ID or not QB_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="QuickBooks not configured")

    import httpx
    import base64
    from datetime import timedelta

    # Extract tenant_id from state
    try:
        tenant_id = state.split(":")[0]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Exchange code for tokens
    credentials = base64.b64encode(f"{QB_CLIENT_ID}:{QB_CLIENT_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            QB_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": QB_REDIRECT_URI,
            },
        )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")

    tokens = response.json()
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=tokens.get("expires_in", 3600))).isoformat()
    refresh_expires_at = (now + timedelta(seconds=tokens.get("x_refresh_token_expires_in", 8726400))).isoformat()

    await db.quickbooks_connections.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "realm_id": realmId,
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_at": expires_at,
                "refresh_expires_at": refresh_expires_at,
                "connected_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
            "$setOnInsert": {"id": str(__import__("uuid").uuid4()), "created_at": now.isoformat()},
        },
        upsert=True,
    )

    # Redirect to frontend settings page
    frontend_url = os.environ.get("FRONTEND_URL", "")
    return RedirectResponse(url=f"{frontend_url}/settings?tab=integrations&qb=connected")


@router.delete("/quickbooks/disconnect")
async def quickbooks_disconnect(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Disconnect QuickBooks integration"""
    await db.quickbooks_connections.delete_one({"tenant_id": tenant_id})
    return {"disconnected": True}


@router.post("/quickbooks/sync-invoices")
async def sync_invoices_to_quickbooks(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Sync recent paid invoices to QuickBooks"""
    qb = await db.quickbooks_connections.find_one({"tenant_id": tenant_id}, {"_id": 0})
    if not qb or not qb.get("access_token"):
        raise HTTPException(status_code=400, detail="QuickBooks not connected")

    import httpx

    realm_id = qb.get("realm_id")
    access_token = qb.get("access_token")
    base_url = (
        "https://sandbox-quickbooks.api.intuit.com"
        if QB_ENVIRONMENT == "sandbox"
        else "https://quickbooks.api.intuit.com"
    )

    # Get recent paid invoices not yet synced
    invoices = await db.invoices.find(
        {"tenant_id": tenant_id, "status": "PAID", "qb_synced": {"$ne": True}},
        {"_id": 0},
    ).to_list(50)

    synced = 0
    errors = []

    async with httpx.AsyncClient() as client:
        for invoice in invoices:
            customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})
            customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() if customer else "Unknown"

            qb_invoice = {
                "Line": [
                    {
                        "Amount": invoice.get("amount", 0),
                        "DetailType": "SalesItemLineDetail",
                        "SalesItemLineDetail": {
                            "ItemRef": {"value": "1", "name": "Services"},
                            "Qty": 1,
                            "UnitPrice": invoice.get("amount", 0),
                        },
                        "Description": f"FieldOS Invoice #{invoice.get('id', '')[:8]}",
                    }
                ],
                "CustomerRef": {"name": customer_name},
                "DueDate": invoice.get("due_date", ""),
                "DocNumber": invoice.get("id", "")[:8].upper(),
                "TxnDate": invoice.get("created_at", "")[:10] if invoice.get("created_at") else "",
            }
            resp = await client.post(
                f"{base_url}/v3/company/{realm_id}/invoice",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"Invoice": qb_invoice},
            )
            if resp.status_code in (200, 201):
                await db.invoices.update_one(
                    {"id": invoice["id"]},
                    {"$set": {"qb_synced": True, "qb_synced_at": datetime.now(timezone.utc).isoformat()}},
                )
                synced += 1
            else:
                errors.append({"invoice_id": invoice.get("id"), "error": resp.text[:200]})

    return {"synced": synced, "errors": errors, "total": len(invoices)}


# ============= CSV EXPORTS =============

@router.get("/export/invoices")
async def export_invoices_csv(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Export invoices as CSV"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status

    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)

    # Enrich with customer data
    for inv in invoices:
        customer = await db.customers.find_one({"id": inv.get("customer_id")}, {"_id": 0})
        if customer:
            inv["customer_name"] = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
            inv["customer_email"] = customer.get("email", "")
            inv["customer_phone"] = customer.get("phone", "")
        else:
            inv["customer_name"] = ""
            inv["customer_email"] = ""
            inv["customer_phone"] = ""

    output = io.StringIO()
    fieldnames = [
        "id", "customer_name", "customer_email", "customer_phone",
        "amount", "currency", "status", "due_date",
        "sent_at", "paid_at", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for inv in invoices:
        writer.writerow({k: inv.get(k, "") for k in fieldnames})

    output.seek(0)
    filename = f"invoices_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/jobs")
async def export_jobs_csv(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Export jobs as CSV"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status

    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)

    for job in jobs:
        customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
        if customer:
            job["customer_name"] = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
            job["customer_phone"] = customer.get("phone", "")
        else:
            job["customer_name"] = ""
            job["customer_phone"] = ""

        prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
        if prop:
            job["address"] = f"{prop.get('address_line1', '')} {prop.get('city', '')} {prop.get('state', '')} {prop.get('postal_code', '')}".strip()
        else:
            job["address"] = ""

        tech = await db.technicians.find_one({"id": job.get("assigned_technician_id")}, {"_id": 0})
        job["technician_name"] = tech.get("name", "") if tech else ""

    output = io.StringIO()
    fieldnames = [
        "id", "job_type", "status", "priority",
        "customer_name", "customer_phone", "address",
        "technician_name", "service_window_start", "service_window_end",
        "quote_amount", "notes", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for job in jobs:
        writer.writerow({k: job.get(k, "") for k in fieldnames})

    output.seek(0)
    filename = f"jobs_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/customers")
async def export_customers_csv(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Export customers as CSV"""
    customers = await db.customers.find({"tenant_id": tenant_id}, {"_id": 0}).sort("created_at", -1).to_list(10000)

    output = io.StringIO()
    fieldnames = [
        "id", "first_name", "last_name", "phone", "email",
        "preferred_channel", "notes", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for customer in customers:
        writer.writerow({k: customer.get(k, "") for k in fieldnames})

    output.seek(0)
    filename = f"customers_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
