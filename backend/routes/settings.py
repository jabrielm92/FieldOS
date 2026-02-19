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
