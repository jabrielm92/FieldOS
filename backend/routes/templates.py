"""Industry template routes - multi-vertical configuration"""
from fastapi import APIRouter, HTTPException

from core.industry_templates import get_template, list_templates

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/industries")
async def get_industry_templates():
    """List all available industry templates (summary view for dropdowns)"""
    return list_templates()


@router.get("/industries/{industry}")
async def get_industry_template(industry: str):
    """Get full template configuration for a specific industry"""
    template = get_template(industry)
    if not template:
        raise HTTPException(status_code=404, detail=f"Industry template '{industry}' not found")
    return template


@router.get("/industries/{industry}/terminology")
async def get_industry_terminology(industry: str):
    """Get just the terminology map for UI label overrides"""
    template = get_template(industry)
    if not template:
        raise HTTPException(status_code=404, detail=f"Industry template '{industry}' not found")
    return {
        "terminology": template["terminology"],
        "booking_noun": template["booking_noun"],
        "staff_noun": template["staff_noun"],
    }


@router.get("/industries/{industry}/service-types")
async def get_industry_service_types(industry: str):
    """Get service types for a specific industry (for job type dropdowns)"""
    template = get_template(industry)
    if not template:
        raise HTTPException(status_code=404, detail=f"Industry template '{industry}' not found")
    return {"service_types": template["service_types"]}
