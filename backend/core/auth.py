"""Authentication helpers: JWT creation/validation, password hashing, FastAPI dependencies"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext

from core.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from core.database import db
from models import UserRole

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, tenant_id: Optional[str], role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# FastAPI dependency functions
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate JWT and return the current user document"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_superadmin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require the current user to have the SUPERADMIN role"""
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return current_user


async def get_tenant_id(current_user: dict = Depends(get_current_user)) -> Optional[str]:
    """Return the tenant_id from the current user's JWT"""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id and current_user.get("role") != UserRole.SUPERADMIN.value:
        raise HTTPException(status_code=400, detail="No tenant associated with user")
    return tenant_id


