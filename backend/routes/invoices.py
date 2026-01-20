"""Invoice routes with Stripe payment integration"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import os
import logging

router = APIRouter(tags=["invoices"])
logger = logging.getLogger(__name__)

# These will be set by init
_db = None
_get_tenant_id_fn = None
_get_current_user_fn = None
_serialize_doc = None
_serialize_docs = None

def init_invoice_routes(db, get_tenant_id_fn, get_current_user_fn, serialize_doc, serialize_docs):
    global _db, _get_tenant_id_fn, _get_current_user_fn, _serialize_doc, _serialize_docs
    _db = db
    _get_tenant_id_fn = get_tenant_id_fn
    _get_current_user_fn = get_current_user_fn
    _serialize_doc = serialize_doc
    _serialize_docs = serialize_docs

async def get_tenant():
    return await _get_tenant_id_fn()

async def get_user():
    return await _get_current_user_fn()


class CreatePaymentLinkRequest(BaseModel):
    invoice_id: str


class StripeWebhookEvent(BaseModel):
    type: str
    data: dict


@router.post("/invoices/{invoice_id}/payment-link")
async def create_payment_link(
    invoice_id: str,
    tenant_id: str = Depends(lambda: get_tenant_id),
    current_user: dict = Depends(lambda: get_current_user)
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


@router.post("/invoices/{invoice_id}/send-payment-link")
async def send_payment_link(
    invoice_id: str,
    tenant_id: str = Depends(lambda: get_tenant_id),
    current_user: dict = Depends(lambda: get_current_user)
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


@router.get("/invoices/overdue")
async def get_overdue_invoices(
    tenant_id: str = Depends(lambda: get_tenant_id),
    current_user: dict = Depends(lambda: get_current_user)
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


@router.get("/reports/revenue")
async def get_revenue_report(
    start_date: str = None,
    end_date: str = None,
    tenant_id: str = Depends(lambda: get_tenant_id),
    current_user: dict = Depends(lambda: get_current_user)
):
    """Get revenue report with payment tracking"""
    # Default to last 30 days
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Get all invoices in date range
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_date, "$lte": end_date + "T23:59:59"}
    }, {"_id": 0}).to_list(10000)
    
    # Calculate metrics
    total_invoiced = sum(float(inv.get('total', 0)) for inv in invoices)
    total_paid = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') == 'PAID')
    total_outstanding = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') in ['SENT', 'PENDING'])
    total_overdue = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') == 'OVERDUE')
    
    # Get jobs for revenue by type
    jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_date, "$lte": end_date + "T23:59:59"}
    }, {"_id": 0}).to_list(10000)
    
    revenue_by_type = {}
    for job in jobs:
        jtype = job.get('job_type', 'OTHER')
        revenue_by_type[jtype] = revenue_by_type.get(jtype, 0) + float(job.get('quoted_amount', 0))
    
    # Daily breakdown
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


# Industry Templates
INDUSTRY_TEMPLATES = {
    "hvac": {
        "name": "HVAC",
        "job_types": ["AC Repair", "Heating Repair", "AC Installation", "Furnace Installation", "Maintenance", "Duct Cleaning", "Thermostat Install"],
        "urgency_options": ["Routine", "Urgent - No Heat/AC", "Emergency - Safety Issue"],
        "default_greeting": "Thank you for calling. How can I help with your heating or cooling needs today?",
        "collect_fields": ["name", "phone", "address", "system_type", "issue", "urgency"]
    },
    "plumbing": {
        "name": "Plumbing",
        "job_types": ["Leak Repair", "Drain Cleaning", "Water Heater", "Toilet Repair", "Faucet Install", "Pipe Repair", "Sewer Line"],
        "urgency_options": ["Routine", "Urgent - Active Leak", "Emergency - Flooding"],
        "default_greeting": "Thank you for calling. What plumbing issue can I help you with today?",
        "collect_fields": ["name", "phone", "address", "issue_location", "issue", "urgency"]
    },
    "electrical": {
        "name": "Electrical",
        "job_types": ["Outlet Repair", "Panel Upgrade", "Wiring", "Lighting Install", "Generator", "EV Charger", "Inspection"],
        "urgency_options": ["Routine", "Urgent - No Power", "Emergency - Sparking/Burning"],
        "default_greeting": "Thank you for calling. What electrical issue can I help you with?",
        "collect_fields": ["name", "phone", "address", "issue", "urgency"]
    },
    "landscaping": {
        "name": "Landscaping",
        "job_types": ["Lawn Care", "Tree Service", "Irrigation", "Hardscape", "Design", "Seasonal Cleanup"],
        "urgency_options": ["Routine", "Priority", "Emergency - Storm Damage"],
        "default_greeting": "Thank you for calling. How can I help with your landscaping needs?",
        "collect_fields": ["name", "phone", "address", "service_type", "property_size"]
    },
    "cleaning": {
        "name": "Cleaning",
        "job_types": ["Regular Cleaning", "Deep Clean", "Move-In/Out", "Post-Construction", "Carpet Cleaning", "Window Cleaning"],
        "urgency_options": ["Routine", "Rush", "Same-Day"],
        "default_greeting": "Thank you for calling. What type of cleaning service are you looking for?",
        "collect_fields": ["name", "phone", "address", "cleaning_type", "property_size", "preferred_date"]
    },
    "general": {
        "name": "General Contractor",
        "job_types": ["Repair", "Installation", "Maintenance", "Inspection", "Consultation", "Emergency"],
        "urgency_options": ["Routine", "Urgent", "Emergency"],
        "default_greeting": "Thank you for calling. How can I help you today?",
        "collect_fields": ["name", "phone", "address", "issue", "urgency"]
    }
}


@router.get("/templates/industries")
async def get_industry_templates():
    """Get available industry templates"""
    return INDUSTRY_TEMPLATES


@router.get("/templates/industries/{industry}")
async def get_industry_template(industry: str):
    """Get specific industry template"""
    if industry not in INDUSTRY_TEMPLATES:
        raise HTTPException(status_code=404, detail="Industry template not found")
    return INDUSTRY_TEMPLATES[industry]
