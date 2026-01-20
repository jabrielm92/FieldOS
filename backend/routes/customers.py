"""Customer routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/customers", tags=["customers"])

# Customer routes remain in server.py for now - will migrate incrementally
