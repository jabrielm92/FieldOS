"""Technician routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs
from models import Technician, TechnicianCreate

router = APIRouter(prefix="/technicians", tags=["technicians"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_technicians(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List technicians"""
    techs = await db.technicians.find(
        {"tenant_id": tenant_id}, {"_id": 0}
    ).to_list(100)
    return serialize_docs(techs)


@router.post("")
async def create_technician(
    data: TechnicianCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new technician"""
    tech = Technician(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )

    tech_dict = tech.model_dump(mode='json')
    await db.technicians.insert_one(tech_dict)

    return serialize_doc(tech_dict)


@router.put("/{technician_id}")
async def update_technician(
    technician_id: str,
    data: TechnicianCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update technician"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.technicians.update_one(
        {"id": technician_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Technician not found")

    tech = await db.technicians.find_one({"id": technician_id}, {"_id": 0})
    return serialize_doc(tech)
