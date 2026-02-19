"""Customer and Property routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs
from models import (
    UserRole,
    Customer, CustomerCreate,
    Property, PropertyCreate,
)

router = APIRouter(tags=["customers"])
logger = logging.getLogger(__name__)


# ============= CUSTOMERS ENDPOINTS =============

@router.get("/customers")
async def list_customers(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List all customers for tenant"""
    # Allow superadmin to query any tenant
    query_tenant_id = tenant_id
    if current_user.get("role") == UserRole.SUPERADMIN.value:
        query_tenant_id = tenant_id or current_user.get("tenant_id")

    customers = await db.customers.find(
        {"tenant_id": query_tenant_id}, {"_id": 0}
    ).to_list(1000)
    return serialize_docs(customers)


@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get customer by ID"""
    customer = await db.customers.find_one(
        {"id": customer_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get associated properties
    properties = await db.properties.find(
        {"customer_id": customer_id, "tenant_id": tenant_id}, {"_id": 0}
    ).to_list(100)

    return {**serialize_doc(customer), "properties": serialize_docs(properties)}


@router.post("/customers")
async def create_customer(
    data: CustomerCreate,
    tenant_id: Optional[str] = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new customer"""
    # For superadmin without tenant_id, require it to be specified
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for customer creation")

    customer = Customer(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )

    customer_dict = customer.model_dump(mode='json')
    await db.customers.insert_one(customer_dict)

    return serialize_doc(customer_dict)


@router.put("/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    data: CustomerCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update customer"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.customers.update_one(
        {"id": customer_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    return serialize_doc(customer)


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a customer and their related data"""
    # Check if customer exists
    customer = await db.customers.find_one({"id": customer_id, "tenant_id": tenant_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Delete related data
    await db.properties.delete_many({"customer_id": customer_id})
    await db.leads.delete_many({"customer_id": customer_id})
    await db.jobs.delete_many({"customer_id": customer_id})
    await db.conversations.delete_many({"customer_id": customer_id})
    await db.messages.delete_many({"customer_id": customer_id})
    await db.quotes.delete_many({"customer_id": customer_id})
    await db.invoices.delete_many({"customer_id": customer_id})

    # Delete customer
    await db.customers.delete_one({"id": customer_id})

    return {"success": True, "message": "Customer and all related data deleted"}


@router.post("/customers/bulk-delete")
async def bulk_delete_customers(
    customer_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete customers and all related data (leads, jobs, properties, conversations)"""
    if not customer_ids:
        raise HTTPException(status_code=400, detail="No customer IDs provided")

    # Delete all related data for each customer
    await db.jobs.delete_many({"customer_id": {"$in": customer_ids}, "tenant_id": tenant_id})
    await db.leads.delete_many({"customer_id": {"$in": customer_ids}, "tenant_id": tenant_id})
    await db.properties.delete_many({"customer_id": {"$in": customer_ids}, "tenant_id": tenant_id})
    await db.conversations.delete_many({"customer_id": {"$in": customer_ids}, "tenant_id": tenant_id})
    await db.messages.delete_many({"customer_id": {"$in": customer_ids}, "tenant_id": tenant_id})
    await db.quotes.delete_many({"customer_id": {"$in": customer_ids}, "tenant_id": tenant_id})
    await db.invoices.delete_many({"customer_id": {"$in": customer_ids}, "tenant_id": tenant_id})

    # Delete customers
    result = await db.customers.delete_many({"id": {"$in": customer_ids}, "tenant_id": tenant_id})

    return {"success": True, "deleted_count": result.deleted_count}


# ============= PROPERTIES ENDPOINTS =============

@router.get("/properties")
async def list_properties(
    customer_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List properties"""
    query = {"tenant_id": tenant_id}
    if customer_id:
        query["customer_id"] = customer_id

    properties = await db.properties.find(query, {"_id": 0}).to_list(1000)
    return serialize_docs(properties)


@router.post("/properties")
async def create_property(
    data: PropertyCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new property"""
    # Verify customer exists
    customer = await db.customers.find_one(
        {"id": data.customer_id, "tenant_id": tenant_id}
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    prop = Property(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )

    prop_dict = prop.model_dump(mode='json')
    await db.properties.insert_one(prop_dict)

    return serialize_doc(prop_dict)


@router.put("/properties/{property_id}")
async def update_property(
    property_id: str,
    data: PropertyCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update property"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.properties.update_one(
        {"id": property_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Property not found")

    prop = await db.properties.find_one({"id": property_id}, {"_id": 0})
    return serialize_doc(prop)
