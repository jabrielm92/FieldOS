"""Branding settings routes"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc
from models import UserRole

router = APIRouter(prefix="/settings", tags=["branding"])
logger = logging.getLogger(__name__)


class BrandingUpdate(BaseModel):
    logo_url: Optional[str] = None
    company_name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    text_on_primary: Optional[str] = None
    portal_title: Optional[str] = None
    portal_welcome_message: Optional[str] = None
    portal_support_email: Optional[str] = None
    portal_support_phone: Optional[str] = None
    white_label_enabled: Optional[bool] = None
    google_review_url: Optional[str] = None
    yelp_review_url: Optional[str] = None
    facebook_review_url: Optional[str] = None


@router.get("/branding")
async def get_branding_settings(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get current tenant branding settings"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    branding = tenant.get("branding", {})
    defaults = {
        "logo_url": None,
        "company_name": tenant.get("name"),
        "primary_color": "#0066CC",
        "secondary_color": "#004499",
        "accent_color": "#FF6600",
        "text_on_primary": "#FFFFFF",
        "portal_title": f"{tenant.get('name')} Customer Portal",
        "portal_welcome_message": "Welcome to your customer portal",
        "portal_support_email": tenant.get("primary_contact_email"),
        "portal_support_phone": tenant.get("primary_phone"),
        "white_label_enabled": False,
        "google_review_url": "",
        "yelp_review_url": "",
        "facebook_review_url": ""
    }

    # Merge defaults with stored branding values
    result = {**defaults}
    for key in defaults:
        if key in branding and branding[key] is not None:
            result[key] = branding[key]

    return result


@router.put("/branding")
async def update_branding_settings(
    data: BrandingUpdate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update tenant branding settings"""
    if current_user.get("role") not in [UserRole.OWNER.value, UserRole.SUPERADMIN.value]:
        raise HTTPException(status_code=403, detail="Only owner can update branding settings")

    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get existing branding and merge
    existing_branding = tenant.get("branding", {})
    update_fields = {k: v for k, v in data.model_dump(mode='json').items() if v is not None}
    new_branding = {**existing_branding, **update_fields}

    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {
            "branding": new_branding,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    updated_tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    return {
        "success": True,
        "branding": updated_tenant.get("branding", {})
    }
