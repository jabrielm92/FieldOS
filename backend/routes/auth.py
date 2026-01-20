"""Authentication routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])

# Auth routes remain in server.py for now due to tight coupling with JWT/password functions
