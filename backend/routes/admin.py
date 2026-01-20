"""Admin routes for superadmin tenant management and Voice AI configuration"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import os

router = APIRouter(prefix="/admin", tags=["admin"])

# These will be injected from server.py
db = None
require_superadmin = None
serialize_doc = None
serialize_docs = None
hash_password = None
UserRole = None
UserStatus = None
User = None
Tenant = None

def init_admin_routes(_db, _require_superadmin, _serialize_doc, _serialize_docs, _hash_password, _UserRole, _UserStatus, _User, _Tenant):
    global db, require_superadmin, serialize_doc, serialize_docs, hash_password, UserRole, UserStatus, User, Tenant
    db = _db
    require_superadmin = _require_superadmin
    serialize_doc = _serialize_doc
    serialize_docs = _serialize_docs
    hash_password = _hash_password
    UserRole = _UserRole
    UserStatus = _UserStatus
    User = _User
    Tenant = _Tenant


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_phone: Optional[str] = None
    booking_mode: Optional[str] = None
    tone_profile: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    twilio_messaging_service_sid: Optional[str] = None
    sms_signature: Optional[str] = None
    service_area: Optional[str] = None
    voice_ai_enabled: Optional[bool] = None
    use_self_hosted_voice: Optional[bool] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_api_key_sid: Optional[str] = None
    twilio_api_key_secret: Optional[str] = None
    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_model: Optional[str] = None
    voice_name: Optional[str] = None
    voice_greeting: Optional[str] = None
    voice_system_prompt: Optional[str] = None
    voice_collect_fields: Optional[List[str]] = None
    voice_business_hours: Optional[dict] = None
    voice_after_hours_message: Optional[str] = None


@router.post("/tenants/{tenant_id}/test-voice")
async def test_voice_ai(tenant_id: str, current_user: dict = Depends(lambda: require_superadmin)):
    """Initiate a test call to verify Voice AI configuration"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.get("voice_ai_enabled"):
        raise HTTPException(status_code=400, detail="Voice AI not enabled for this tenant")
    
    if not tenant.get("twilio_account_sid") or not tenant.get("twilio_auth_token"):
        raise HTTPException(status_code=400, detail="Twilio credentials not configured")
    
    if not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="Twilio phone number not configured")
    
    # Import Twilio client
    try:
        from twilio.rest import Client
        client = Client(tenant["twilio_account_sid"], tenant["twilio_auth_token"])
        
        # Get the webhook URL from environment
        webhook_base = os.environ.get("RAILWAY_PUBLIC_DOMAIN", os.environ.get("BACKEND_URL", ""))
        if not webhook_base:
            raise HTTPException(status_code=400, detail="Webhook URL not configured")
        
        if not webhook_base.startswith("http"):
            webhook_base = f"https://{webhook_base}"
        
        # Make test call to the tenant's own number (will trigger voicemail/IVR)
        call = client.calls.create(
            to=tenant["twilio_phone_number"],
            from_=tenant["twilio_phone_number"],
            url=f"{webhook_base}/api/v1/voice/inbound?test=true",
            status_callback=f"{webhook_base}/api/v1/voice/status",
            timeout=30
        )
        
        return {
            "success": True,
            "message": "Test call initiated",
            "call_sid": call.sid,
            "status": call.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate test call: {str(e)}")
