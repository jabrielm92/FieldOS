"""Quotes routes"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from core.database import db
from core.auth import get_current_user, get_tenant_id
from core.utils import serialize_doc, serialize_docs
from models import Quote, QuoteCreate

router = APIRouter(prefix="/quotes", tags=["quotes"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_quotes(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List quotes"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status

    quotes = await db.quotes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

    for quote in quotes:
        customer = await db.customers.find_one({"id": quote.get("customer_id")}, {"_id": 0})
        quote["customer"] = serialize_doc(customer) if customer else None
        if quote.get("property_id"):
            prop = await db.properties.find_one({"id": quote.get("property_id")}, {"_id": 0})
            quote["property"] = serialize_doc(prop) if prop else None

    return serialize_docs(quotes)


@router.post("")
async def create_quote(
    data: QuoteCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new quote"""
    quote = Quote(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )

    quote_dict = quote.model_dump(mode='json')
    await db.quotes.insert_one(quote_dict)

    return serialize_doc(quote_dict)


@router.put("/{quote_id}")
async def update_quote(
    quote_id: str,
    data: QuoteCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update quote"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.quotes.update_one(
        {"id": quote_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Quote not found")

    quote = await db.quotes.find_one({"id": quote_id}, {"_id": 0})
    return serialize_doc(quote)
