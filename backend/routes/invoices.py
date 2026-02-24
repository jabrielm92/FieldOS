"""Invoice routes - CRUD, payment links, and Stripe webhook"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import os
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs
from models import Invoice, InvoiceCreate, InvoiceStatus

router = APIRouter(prefix="/invoices", tags=["invoices"])
logger = logging.getLogger(__name__)


# ============= INVOICES CRUD =============

@router.get("")
async def list_invoices(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List invoices with optional filters"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    if customer_id:
        query["customer_id"] = customer_id

    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    for invoice in invoices:
        customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})
        job = await db.jobs.find_one({"id": invoice.get("job_id")}, {"_id": 0})
        invoice["customer"] = serialize_doc(customer) if customer else None
        invoice["job"] = serialize_doc(job) if job else None

    return serialize_docs(invoices)


@router.get("/overdue")
async def get_overdue_invoices(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get list of overdue invoices"""
    today = datetime.now(timezone.utc).isoformat()[:10]

    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": {"$in": ["SENT", "PENDING"]},
        "due_date": {"$lt": today}
    }, {"_id": 0}).to_list(1000)

    # Mark as overdue
    for inv in invoices:
        if inv.get("status") != "OVERDUE":
            await db.invoices.update_one(
                {"id": inv["id"]},
                {"$set": {"status": "OVERDUE", "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            inv["status"] = "OVERDUE"

    return serialize_docs(invoices)


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get invoice details"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})
    job = await db.jobs.find_one({"id": invoice.get("job_id")}, {"_id": 0})

    return {
        **serialize_doc(invoice),
        "customer": serialize_doc(customer) if customer else None,
        "job": serialize_doc(job) if job else None
    }


@router.post("")
async def create_invoice(
    data: InvoiceCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new invoice"""
    # Verify customer exists
    customer = await db.customers.find_one({"id": data.customer_id, "tenant_id": tenant_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Verify job exists
    job = await db.jobs.find_one({"id": data.job_id, "tenant_id": tenant_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    invoice = Invoice(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )

    invoice_dict = invoice.model_dump(mode='json')
    await db.invoices.insert_one(invoice_dict)

    return serialize_doc(invoice_dict)


@router.put("/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    data: InvoiceCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update invoice"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    return serialize_doc(invoice)


@router.post("/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Mark invoice as paid"""
    result = await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": {
            "status": InvoiceStatus.PAID.value,
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {"success": True, "message": "Invoice marked as paid"}


# ============= PAYMENT LINKS (STRIPE) =============

@router.post("/{invoice_id}/payment-link")
async def create_payment_link(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe payment link for an invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.get("status") == "PAID":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    stripe_key = tenant.get("stripe_secret_key") or os.environ.get("STRIPE_SECRET_KEY")

    if not stripe_key:
        raise HTTPException(status_code=400, detail="Stripe not configured")

    customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})

    try:
        import stripe
        stripe.api_key = stripe_key

        # Create Stripe payment link
        amount_cents = int(float(invoice.get("total", 0)) * 100)

        # Create a price for this invoice
        price = stripe.Price.create(
            unit_amount=amount_cents,
            currency="usd",
            product_data={
                "name": f"Invoice #{invoice.get('invoice_number', invoice_id[:8])}",
                "metadata": {
                    "invoice_id": invoice_id,
                    "tenant_id": tenant_id
                }
            }
        )

        # Create payment link
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            metadata={
                "invoice_id": invoice_id,
                "tenant_id": tenant_id,
                "customer_id": invoice.get("customer_id")
            },
            after_completion={
                "type": "redirect",
                "redirect": {"url": f"{os.environ.get('FRONTEND_URL', '')}/payment-success?invoice={invoice_id}"}
            }
        )

        # Save payment link to invoice
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {
                "stripe_payment_link": payment_link.url,
                "stripe_payment_link_id": payment_link.id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        return {
            "success": True,
            "payment_link": payment_link.url,
            "payment_link_id": payment_link.id
        }
    except Exception as e:
        logger.error(f"Failed to create Stripe payment link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment link: {str(e)}")


@router.post("/{invoice_id}/send-payment-link")
async def send_payment_link(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send payment link to customer via SMS"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not invoice.get("stripe_payment_link"):
        raise HTTPException(status_code=400, detail="Payment link not created yet")

    customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured")

    message = f"Hi {customer.get('name', 'there')}! Your invoice from {tenant['name']} for ${invoice.get('total', 0):.2f} is ready. Pay securely here: {invoice['stripe_payment_link']}"
    if tenant.get("sms_signature"):
        message += f" {tenant['sms_signature']}"

    try:
        from services.twilio_service import twilio_service
        await twilio_service.send_sms(
            to_phone=customer["phone"],
            message=message,
            from_phone=tenant["twilio_phone_number"]
        )

        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {
                "payment_link_sent_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        return {"success": True, "message": "Payment link sent to customer"}
    except Exception as e:
        logger.error(f"Failed to send payment link SMS: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")


# ============= STRIPE WEBHOOK =============

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for payment updates"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    try:
        import stripe
        if webhook_secret and sig_header:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            import json
            event = json.loads(payload)

        # Handle successful payment
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            invoice_id = session.get("metadata", {}).get("invoice_id")

            if invoice_id:
                await db.invoices.update_one(
                    {"id": invoice_id},
                    {"$set": {
                        "status": "PAID",
                        "paid_at": datetime.now(timezone.utc).isoformat(),
                        "stripe_payment_intent": session.get("payment_intent"),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                logger.info(f"Invoice {invoice_id} marked as paid via Stripe")

        elif event["type"] == "payment_link.completed":
            metadata = event["data"]["object"].get("metadata", {})
            invoice_id = metadata.get("invoice_id")

            if invoice_id:
                await db.invoices.update_one(
                    {"id": invoice_id},
                    {"$set": {
                        "status": "PAID",
                        "paid_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )

        return {"received": True}
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============= PUBLIC PAYMENT PAGE =============

@router.get("/public/{token}")
async def get_invoice_public(token: str):
    """
    Public endpoint — no auth required.
    Returns invoice data for the customer-facing payment page at /pay/:token.
    """
    invoice = await db.invoices.find_one(
        {"payment_link_token": token}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found or link has expired")

    # Fetch tenant branding (logo, company name)
    tenant = await db.tenants.find_one({"id": invoice.get("tenant_id")}, {"_id": 0})
    customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})

    return {
        "id": invoice["id"],
        "invoice_number": invoice.get("invoice_number", f"INV-{invoice['id'][:6].upper()}"),
        "amount": invoice.get("amount", 0),
        "status": invoice.get("status", "SENT"),
        "due_date": invoice.get("due_date"),
        "notes": invoice.get("notes", ""),
        "stripe_payment_link": invoice.get("stripe_payment_link"),
        "paid_at": invoice.get("paid_at"),
        "customer": {
            "name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() if customer else "Customer",
        } if customer else None,
        "company": {
            "name": tenant.get("name", "FieldOS") if tenant else "FieldOS",
            "logo_url": (tenant.get("branding") or {}).get("logo_url") if tenant else None,
            "primary_color": (tenant.get("branding") or {}).get("primary_color", "#0066CC") if tenant else "#0066CC",
            "phone": tenant.get("primary_phone") if tenant else None,
        } if tenant else {"name": "FieldOS", "primary_color": "#0066CC"},
    }
