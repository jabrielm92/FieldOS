"""
Billing routes - SaaS subscription management for FieldOS tenants
Tenants pay FieldOS via Stripe Billing (subscriptions).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import os
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)

# Plan definitions - pricing is passed inline to Stripe via price_data (no pre-created price IDs needed)
# Pricing model: one-time setup fee + monthly retainer (no trial)
# Monthly costs covered per tenant: Twilio (~$8), OpenAI (~$25), ElevenLabs (~$15),
# infrastructure (~$8), support — minimum ~$56/mo before margin.
PLANS = {
    "STARTER": {
        "name": "Starter",
        "tagline": "For solo operators & small crews",
        "setup_fee": 497,
        "price_monthly": 149,
        "limits": {
            "jobs_per_month": 150,
            "technicians": 3,
            "users": 5,
        },
        "features": [
            "Up to 3 technicians",
            "Jobs, customers & scheduling",
            "Invoicing + Stripe payment collection",
            "Customer self-service portal",
            "Automated SMS reminders",
            "Dispatch board",
            "Revenue reports & CSV export",
            "Email support",
        ],
    },
    "PRO": {
        "name": "Pro",
        "tagline": "For growing field service companies",
        "setup_fee": 797,
        "price_monthly": 299,
        "limits": {
            "jobs_per_month": -1,  # unlimited
            "technicians": 10,
            "users": 15,
        },
        "features": [
            "Up to 10 technicians",
            "Everything in Starter",
            "AI Voice receptionist (24/7 call answering)",
            "AI SMS assistant (auto-qualify leads)",
            "Automated booking & lead capture",
            "SMS marketing campaigns",
            "QuickBooks sync",
            "Priority support",
        ],
    },
    "ENTERPRISE": {
        "name": "Enterprise",
        "tagline": "For multi-location & high-volume operations",
        "setup_fee": 1497,
        "price_monthly": 549,
        "limits": {
            "jobs_per_month": -1,
            "technicians": -1,
            "users": -1,
        },
        "features": [
            "Unlimited technicians & users",
            "Everything in Pro",
            "White-label branding & custom domain",
            "Dedicated onboarding & training",
            "Custom AI voice & SMS prompts",
            "Multi-location support",
            "SLA-backed support",
            "Quarterly business reviews",
        ],
    },
}


class CreateCheckoutRequest(BaseModel):
    plan: str  # STARTER, PRO, ENTERPRISE
    success_url: str
    cancel_url: str


class CreatePortalRequest(BaseModel):
    return_url: str


@router.get("/plans")
async def get_plans():
    """Return available subscription plans (no auth required for pricing page)"""
    return {"plans": PLANS}


@router.get("/subscription")
async def get_subscription(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Get the current tenant's subscription status"""
    sub = await db.subscriptions.find_one({"tenant_id": tenant_id}, {"_id": 0})
    if not sub:
        return {
            "plan": None,
            "status": "INACTIVE",
            "current_period_end": None,
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
        }
    return serialize_doc(sub)


@router.post("/checkout")
async def create_checkout_session(
    body: CreateCheckoutRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Create a Stripe Checkout session for a subscription plan"""
    try:
        import stripe
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe library not installed")

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = stripe_key

    plan = body.plan.upper()
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan}")

    plan_data = PLANS[plan]
    price_monthly_cents = plan_data["price_monthly"] * 100
    setup_fee_cents = plan_data["setup_fee"] * 100

    # Get or create Stripe customer for this tenant
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    sub = await db.subscriptions.find_one({"tenant_id": tenant_id}, {"_id": 0})
    stripe_customer_id = sub.get("stripe_customer_id") if sub else None

    if not stripe_customer_id:
        customer = stripe.Customer.create(
            email=tenant.get("primary_contact_email"),
            name=tenant.get("name"),
            metadata={"tenant_id": tenant_id, "tenant_slug": tenant.get("slug", "")},
        )
        stripe_customer_id = customer.id

    # Create checkout session - no trial, payment required immediately
    # Setup fee is charged as a one-time invoice item on the first invoice
    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        mode="subscription",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"FieldOS {plan_data['name']} Plan"},
                    "unit_amount": price_monthly_cents,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }
        ],
        success_url=body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=body.cancel_url,
        metadata={"tenant_id": tenant_id, "plan": plan},
        subscription_data={
            "metadata": {"tenant_id": tenant_id, "plan": plan},
            "add_invoice_items": [
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"FieldOS {plan_data['name']} Setup & Onboarding Fee"},
                        "unit_amount": setup_fee_cents,
                    },
                    "quantity": 1,
                }
            ],
        },
        allow_promotion_codes=True,
        billing_address_collection="auto",
    )

    # Upsert subscription record
    now = datetime.now(timezone.utc).isoformat()
    await db.subscriptions.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "stripe_customer_id": stripe_customer_id,
                "stripe_checkout_session_id": session.id,
                "plan": plan,
                "status": "PENDING_PAYMENT",
                "updated_at": now,
            },
            "$setOnInsert": {
                "id": str(__import__("uuid").uuid4()),
                "created_at": now,
            },
        },
        upsert=True,
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
async def create_billing_portal(
    body: CreatePortalRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    """Create a Stripe Billing Portal session for self-serve plan management"""
    try:
        import stripe
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe library not installed")

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = stripe_key

    sub = await db.subscriptions.find_one({"tenant_id": tenant_id}, {"_id": 0})
    if not sub or not sub.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No billing account found. Please subscribe first.")

    session = stripe.billing_portal.Session.create(
        customer=sub["stripe_customer_id"],
        return_url=body.return_url,
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_subscription_webhook(request: Request):
    """Handle Stripe subscription lifecycle webhooks"""
    try:
        import stripe
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe library not installed")

    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    if not stripe_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = stripe_key

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        if webhook_secret and sig_header:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = stripe.Event.construct_from(
                __import__("json").loads(payload), stripe.api_key
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

    now = datetime.now(timezone.utc).isoformat()
    event_type = event["type"]
    data_obj = event["data"]["object"]

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        tenant_id = data_obj.get("metadata", {}).get("tenant_id")
        if tenant_id:
            plan = data_obj.get("metadata", {}).get("plan", "STARTER")
            status_map = {
                "active": "ACTIVE",
                "past_due": "PAST_DUE",
                "canceled": "CANCELED",
                "unpaid": "UNPAID",
                "incomplete": "PENDING_PAYMENT",
                "incomplete_expired": "CANCELED",
            }
            stripe_status = data_obj.get("status", "active")
            mapped_status = status_map.get(stripe_status, "ACTIVE")

            period_start = datetime.fromtimestamp(
                data_obj["current_period_start"], tz=timezone.utc
            ).isoformat() if data_obj.get("current_period_start") else None
            period_end = datetime.fromtimestamp(
                data_obj["current_period_end"], tz=timezone.utc
            ).isoformat() if data_obj.get("current_period_end") else None
            trial_end = datetime.fromtimestamp(
                data_obj["trial_end"], tz=timezone.utc
            ).isoformat() if data_obj.get("trial_end") else None

            await db.subscriptions.update_one(
                {"tenant_id": tenant_id},
                {
                    "$set": {
                        "stripe_subscription_id": data_obj["id"],
                        "stripe_customer_id": data_obj["customer"],
                        "plan": plan,
                        "status": mapped_status,
                        "current_period_start": period_start,
                        "current_period_end": period_end,
                        "trial_end": trial_end,
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "id": str(__import__("uuid").uuid4()),
                        "tenant_id": tenant_id,
                        "created_at": now,
                    },
                },
                upsert=True,
            )
            # Also update tenant record with plan info
            await db.tenants.update_one(
                {"id": tenant_id},
                {"$set": {"subscription_plan": plan, "subscription_status": mapped_status, "updated_at": now}},
            )

    elif event_type == "customer.subscription.deleted":
        tenant_id = data_obj.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await db.subscriptions.update_one(
                {"tenant_id": tenant_id},
                {"$set": {"status": "CANCELED", "canceled_at": now, "updated_at": now}},
            )
            await db.tenants.update_one(
                {"id": tenant_id},
                {"$set": {"subscription_status": "CANCELED", "updated_at": now}},
            )

    elif event_type == "checkout.session.completed":
        tenant_id = data_obj.get("metadata", {}).get("tenant_id")
        if tenant_id:
            await db.subscriptions.update_one(
                {"tenant_id": tenant_id},
                {
                    "$set": {
                        "stripe_customer_id": data_obj.get("customer"),
                        "stripe_checkout_session_id": data_obj["id"],
                        "updated_at": now,
                    }
                },
            )

    return {"received": True}
