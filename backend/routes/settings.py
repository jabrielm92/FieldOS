"""Settings routes - tenant settings for tenant owners"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc
from models import UserRole

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_phone: Optional[str] = None
    booking_mode: Optional[str] = None
    tone_profile: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    twilio_messaging_service_sid: Optional[str] = None
    sms_signature: Optional[str] = None
    service_area: Optional[str] = None
    # Voice AI Configuration
    voice_ai_enabled: Optional[bool] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_api_key_sid: Optional[str] = None
    twilio_api_key_secret: Optional[str] = None
    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_model: Optional[str] = None
    voice_name: Optional[str] = None
    voice_greeting: Optional[str] = None
    voice_system_prompt: Optional[str] = None
    voice_collect_fields: Optional[List[str]] = None
    voice_business_hours: Optional[dict] = None
    voice_after_hours_message: Optional[str] = None


@router.get("/tenant")
async def get_tenant_settings(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get current tenant's settings"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Remove sensitive fields for non-superadmin
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        sensitive_fields = ["twilio_auth_token", "twilio_api_key_secret", "openai_api_key", "elevenlabs_api_key"]
        for field in sensitive_fields:
            if field in tenant:
                tenant[field] = "********" if tenant[field] else None

    return serialize_doc(tenant)


@router.put("/tenant")
async def update_tenant_settings(
    data: TenantUpdate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update current tenant's settings (owner only)"""
    if current_user.get("role") not in [UserRole.OWNER.value, UserRole.SUPERADMIN.value]:
        raise HTTPException(status_code=403, detail="Only owner can update tenant settings")

    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = {k: v for k, v in data.model_dump(mode='json').items() if v is not None}

    # Non-superadmins can't update sensitive fields
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        sensitive_fields = ["twilio_account_sid", "twilio_auth_token", "twilio_api_key_sid",
                          "twilio_api_key_secret", "openai_api_key", "elevenlabs_api_key"]
        for field in sensitive_fields:
            update_data.pop(field, None)

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.tenants.update_one({"id": tenant_id}, {"$set": update_data})

    updated = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    return serialize_doc(updated)


# ──────────────────────────────────────────────────────────────────────────────
# Invoice Settings
# ──────────────────────────────────────────────────────────────────────────────

class InvoiceSettingsUpdate(BaseModel):
    invoice_prefix: Optional[str] = None
    default_payment_terms: Optional[int] = None
    default_tax_rate: Optional[float] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    invoice_footer_text: Optional[str] = None
    payment_instructions: Optional[str] = None
    auto_reminder_enabled: Optional[bool] = None
    auto_reminder_days: Optional[List[int]] = None
    stripe_secret_key: Optional[str] = None


@router.get("/invoice")
async def get_invoice_settings(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get invoice settings for tenant"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    settings = tenant.get("invoice_settings") or {}
    # Mask Stripe key
    stripe_key = tenant.get("stripe_secret_key", "")
    if stripe_key and len(stripe_key) > 8:
        stripe_key = stripe_key[:7] + "..." + stripe_key[-4:]

    return {
        **settings,
        "stripe_secret_key": stripe_key,
        "stripe_configured": bool(tenant.get("stripe_secret_key")),
    }


@router.put("/invoice")
async def update_invoice_settings(
    data: InvoiceSettingsUpdate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update invoice settings"""
    if current_user.get("role") not in [UserRole.OWNER.value, UserRole.SUPERADMIN.value]:
        raise HTTPException(status_code=403, detail="Only owner can update settings")

    update_fields = {k: v for k, v in data.model_dump(mode="json").items() if v is not None}

    # Stripe key is stored at tenant root level, not in invoice_settings
    stripe_key = update_fields.pop("stripe_secret_key", None)

    set_data = {f"invoice_settings.{k}": v for k, v in update_fields.items()}
    if stripe_key and not stripe_key.startswith("sk_") is False:
        set_data["stripe_secret_key"] = stripe_key
    elif stripe_key and "..." not in stripe_key:
        set_data["stripe_secret_key"] = stripe_key

    set_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.tenants.update_one({"id": tenant_id}, {"$set": set_data})

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    settings = tenant.get("invoice_settings") or {}
    return {"success": True, **settings}
