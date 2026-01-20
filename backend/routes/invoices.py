"""Invoice routes with Stripe payment integration"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import os
import logging

router = APIRouter(tags=["invoices"])
logger = logging.getLogger(__name__)

# Injected dependencies
db = None
get_tenant_id = None
get_current_user = None
serialize_doc = None
serialize_docs = None

def init_invoice_routes(_db, _get_tenant_id, _get_current_user, _serialize_doc, _serialize_docs):
    global db, get_tenant_id, get_current_user, serialize_doc, serialize_docs
    db = _db
    get_tenant_id = _get_tenant_id
    get_current_user = _get_current_user
    serialize_doc = _serialize_doc
    serialize_docs = _serialize_docs


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
