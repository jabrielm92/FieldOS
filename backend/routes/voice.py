"""Voice AI routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/voice", tags=["voice"])

# Voice routes remain in server.py due to WebSocket complexity
