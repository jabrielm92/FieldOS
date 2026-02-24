"""Setup routes - one-time admin creation and initial configuration"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4
import logging

from core.database import db
from core.auth import hash_password, require_superadmin, get_current_user
from core.utils import serialize_doc

router = APIRouter(tags=["setup"])
logger = logging.getLogger(__name__)


@router.post("/setup/admin")
async def setup_admin_user():
    """
    One-time setup to create the superadmin user.
    Only works if no superadmin exists.
    """
    # Check if superadmin already exists
    existing = await db.users.find_one({"role": "SUPERADMIN"}, {"_id": 0})
    if existing:
        return {"success": False, "message": "Admin user already exists"}

    # Create superadmin
    user_id = str(uuid4())
    password_hash = hash_password("Finao028!")

    admin_user = {
        "id": user_id,
        "email": "jabriel@arisolutionsinc.com",
        "password_hash": password_hash,
        "name": "Jabriel Martinez",
        "role": "SUPERADMIN",
        "tenant_id": None,
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.users.insert_one(admin_user)
    logger.info(f"Created superadmin user: {admin_user['email']}")

    return {"success": True, "message": "Admin user created successfully", "email": admin_user["email"]}


@router.get("/tenants")
async def list_tenants(
    current_user: dict = Depends(require_superadmin)
):
    """List all tenants (superadmin only)"""
    from core.utils import serialize_docs
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(1000)
    return serialize_docs(tenants)


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    current_user: dict = Depends(require_superadmin)
):
    """Get tenant by ID (superadmin only)"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return serialize_doc(tenant)
