"""Auth routes - login, logout, and current user"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, verify_password, create_access_token
from models import LoginRequest, TokenResponse, UserResponse, UserStatus, UserRole, generate_id, utc_now

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    user = await db.users.find_one({"email": request.email}, {"_id": 0})

    if not user or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("status") == UserStatus.DISABLED.value:
        raise HTTPException(status_code=401, detail="Account is disabled")

    token = create_access_token(user["id"], user.get("tenant_id"), user["role"])

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            status=user["status"],
            tenant_id=user.get("tenant_id")
        )
    )


@router.post("/logout")
async def logout():
    """Logout user (client should discard token)"""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        status=current_user["status"],
        tenant_id=current_user.get("tenant_id")
    )


class RegisterRequest(BaseModel):
    business_name: str
    owner_name: str
    email: EmailStr
    password: str
    phone: str
    industry_slug: Optional[str] = "general"

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Self-service tenant registration"""
    import re
    from core.auth import hash_password, create_access_token

    # Check email not already in use
    existing = await db.users.find_one({"email": request.email})
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    # Generate slug from business name
    slug = re.sub(r'[^a-z0-9-]', '', re.sub(r'\s+', '-', request.business_name.lower().strip()))
    slug = slug[:40]
    # Ensure slug is unique
    base_slug = slug
    counter = 1
    while await db.tenants.find_one({"slug": slug}):
        slug = f"{base_slug}-{counter}"
        counter += 1

    now = utc_now()
    tenant_id = generate_id()
    user_id = generate_id()

    # Create tenant
    tenant_doc = {
        "id": tenant_id,
        "name": request.business_name,
        "slug": slug,
        "primary_contact_name": request.owner_name,
        "primary_contact_email": request.email,
        "primary_phone": request.phone,
        "timezone": "America/New_York",
        "booking_mode": "TIME_WINDOWS",
        "tone_profile": "PROFESSIONAL",
        "industry_template": request.industry_slug or "general",
        "voice_ai_enabled": False,
        "subscription_plan": None,
        "subscription_status": "INACTIVE",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.tenants.insert_one(tenant_doc)

    # Create owner user
    user_doc = {
        "id": user_id,
        "tenant_id": tenant_id,
        "email": request.email,
        "name": request.owner_name,
        "role": "OWNER",
        "status": "ACTIVE",
        "password_hash": hash_password(request.password),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(user_id, tenant_id, "OWNER")

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=request.email,
            name=request.owner_name,
            role=UserRole.OWNER,
            status=UserStatus.ACTIVE,
            tenant_id=tenant_id,
        )
    )
