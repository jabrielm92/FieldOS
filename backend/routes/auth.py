"""Auth routes - login, logout, and current user"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, verify_password, create_access_token
from models import LoginRequest, TokenResponse, UserResponse, UserStatus

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
