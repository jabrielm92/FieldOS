"""
FieldOS Backend - Main FastAPI Application
Multi-tenant Revenue & Operations OS for field service companies
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request, Form, WebSocket, WebSocketDisconnect, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from uuid import uuid4

from core.config import validate_security_settings, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
from core.app_setup import configure_cors
from core.lifecycle import shutdown_resources

from models import (
    # Enums
    UserRole, UserStatus, LeadSource, LeadChannel, LeadStatus, Urgency,
    JobType, JobPriority, JobStatus, JobCreatedBy, QuoteStatus, InvoiceStatus,
    ConversationStatus, MessageDirection, SenderType, PreferredChannel,
    CampaignStatus, RecipientStatus, BookingMode, ToneProfile,
    # Models
    Tenant, TenantCreate, TenantResponse, TenantSummary,
    User, UserCreate, UserResponse,
    Customer, CustomerCreate,
    Property, PropertyCreate,
    Technician, TechnicianCreate,
    Lead, LeadCreate,
    Job, JobCreate,
    Quote, QuoteCreate,
    Invoice, InvoiceCreate,
    Conversation, Message, MessageCreate,
    Campaign, CampaignCreate, CampaignRecipient,
    # Auth
    LoginRequest, TokenResponse,
    # Web Form
    WebFormLeadRequest
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer(auto_error=False)

# Security validation (fail-fast in production)
validate_security_settings()

# Create the main app
app = FastAPI(title="FieldOS API", version="1.0.0")

# Create routers
api_router = APIRouter(prefix="/api")
v1_router = APIRouter(prefix="/v1")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============= UTILITY FUNCTIONS =============

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, tenant_id: Optional[str], role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def serialize_doc(doc: dict) -> dict:
    """Serialize MongoDB document for JSON response"""
    if doc is None:
        return None
    result = {k: v for k, v in doc.items() if k != '_id'}
    # Convert datetime objects to ISO strings
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result


def calculate_quote_amount(job_type: str, urgency: str = None) -> float:
    """Calculate quote amount based on job type and urgency"""
    # Base prices by job type (handle both INSTALL and INSTALLATION)
    base_prices = {
        "DIAGNOSTIC": 89.00,
        "REPAIR": 250.00,
        "MAINTENANCE": 149.00,
        "INSTALL": 1500.00,
        "INSTALLATION": 1500.00,  # Alias
        "INSPECTION": 75.00,
    }
    
    # Urgency multipliers
    urgency_multipliers = {
        "EMERGENCY": 1.5,  # 50% extra for emergency
        "URGENT": 1.25,    # 25% extra for urgent
        "ROUTINE": 1.0,    # Standard price
    }
    
    base = base_prices.get(job_type, 150.00)
    multiplier = urgency_multipliers.get(urgency, 1.0)
    
    return round(base * multiplier, 2)


def serialize_docs(docs: list) -> list:
    """Serialize list of MongoDB documents"""
    return [serialize_doc(doc) for doc in docs]


def normalize_phone_e164(phone: str) -> str:
    """
    Normalize phone number to E.164 format (+1XXXXXXXXXX).
    Required for SMS services like Twilio.
    """
    if not phone:
        return ""
    # Remove all non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())
    # Handle +1 prefix already present
    if phone.startswith('+1') and len(digits) == 11 and digits.startswith('1'):
        return '+' + digits
    # Add country code if missing (assume US +1)
    if len(digits) == 10:
        digits = '1' + digits
    elif len(digits) == 11 and digits.startswith('1'):
        pass  # Already has country code
    else:
        # Return as-is with + prefix if can't normalize
        return '+' + digits if digits else ""
    # Add + prefix for E.164 format
    return '+' + digits


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Validate JWT and return current user info"""
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
    """Require superadmin role"""
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return current_user


async def get_tenant_id(current_user: dict = Depends(get_current_user)) -> Optional[str]:
    """Get tenant_id for scoped queries"""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id and current_user.get("role") != UserRole.SUPERADMIN.value:
        raise HTTPException(status_code=400, detail="No tenant associated with user")
    return tenant_id




# ============= AUTH ENDPOINTS =============

@v1_router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    user = await db.users.find_one({"email": request.email}, {"_id": 0})

    if not user or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("status") == UserStatus.DISABLED.value:
        raise HTTPException(status_code=401, detail="Account is disabled")

    token = create_access_token(user["id"], user.get("tenant_id"), user["role"])

    tenant_summary = None
    if user.get("tenant_id"):
        tenant_doc = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0})
        if tenant_doc:
            industry_slug = tenant_doc.get("industry_slug")
            onboarding_completed = tenant_doc.get("onboarding_completed", False) or bool(industry_slug)
            tenant_summary = TenantSummary(
                id=tenant_doc["id"],
                name=tenant_doc.get("name", ""),
                slug=tenant_doc.get("slug"),
                industry_slug=industry_slug,
                onboarding_completed=onboarding_completed,
            )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            status=user["status"],
            tenant_id=user.get("tenant_id"),
            tenant=tenant_summary,
        )
    )


@v1_router.post("/auth/logout")
async def logout():
    """Logout user (client should discard token)"""
    return {"message": "Logged out successfully"}


@v1_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    tenant_summary = None
    if current_user.get("tenant_id"):
        tenant_doc = await db.tenants.find_one({"id": current_user["tenant_id"]}, {"_id": 0})
        if tenant_doc:
            industry_slug = tenant_doc.get("industry_slug")
            onboarding_completed = tenant_doc.get("onboarding_completed", False) or bool(industry_slug)
            tenant_summary = TenantSummary(
                id=tenant_doc["id"],
                name=tenant_doc.get("name", ""),
                slug=tenant_doc.get("slug"),
                industry_slug=industry_slug,
                onboarding_completed=onboarding_completed,
            )

    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        status=current_user["status"],
        tenant_id=current_user.get("tenant_id"),
        tenant=tenant_summary,
    )


class RegisterRequest(BaseModel):
    business_name: str
    owner_name: str
    email: str
    password: str
    phone: str
    industry_slug: Optional[str] = "general"


@v1_router.post("/auth/register", response_model=TokenResponse)
async def register_tenant(request: RegisterRequest):
    """Self-service tenant registration - creates new tenant + owner user"""
    import re
    from models import generate_id, utc_now

    existing = await db.users.find_one({"email": request.email})
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    slug = re.sub(r'[^a-z0-9-]', '', re.sub(r'\s+', '-', request.business_name.lower().strip()))
    slug = slug[:40] or "tenant"
    base_slug = slug
    counter = 1
    while await db.tenants.find_one({"slug": slug}):
        slug = f"{base_slug}-{counter}"
        counter += 1

    now = utc_now()
    tenant_id = generate_id()
    user_id = generate_id()

    tenant_doc = {
        "id": tenant_id,
        "name": request.business_name,
        "slug": slug,
        "primary_contact_name": request.owner_name,
        "primary_contact_email": request.email,
        "primary_phone": request.phone,
        "timezone": "America/New_York",
        "booking_mode": "TIME_WINDOWS",
        "tone_profile": "PROFESSIONAL",
        "industry_template": request.industry_slug or "general",
        "voice_ai_enabled": False,
        "subscription_plan": None,
        "subscription_status": "INACTIVE",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.tenants.insert_one(tenant_doc)

    user_doc = {
        "id": user_id,
        "tenant_id": tenant_id,
        "email": request.email,
        "name": request.owner_name,
        "role": "OWNER",
        "status": "ACTIVE",
        "password_hash": hash_password(request.password),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token(user_id, tenant_id, "OWNER")

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=request.email,
            name=request.owner_name,
            role=UserRole.OWNER,
            status=UserStatus.ACTIVE,
            tenant_id=tenant_id,
        )
    )


# ============= SUPERADMIN ENDPOINTS =============

@v1_router.get("/admin/tenants")
async def list_tenants(current_user: dict = Depends(require_superadmin)):
    """List all tenants (superadmin only)"""
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(1000)
    
    # Add summary stats for each tenant
    for tenant in tenants:
        tenant_id = tenant["id"]
        # Count leads in last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        leads_count = await db.leads.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": thirty_days_ago.isoformat()}
        })
        jobs_count = await db.jobs.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": thirty_days_ago.isoformat()}
        })
        tenant["leads_last_30d"] = leads_count
        tenant["jobs_last_30d"] = jobs_count
    
    return serialize_docs(tenants)


@v1_router.post("/admin/tenants")
async def create_tenant(data: TenantCreate, current_user: dict = Depends(require_superadmin)):
    """Create a new tenant with owner user"""
    # Check slug uniqueness
    existing = await db.tenants.find_one({"slug": data.slug})
    if existing:
        raise HTTPException(status_code=400, detail="Tenant slug already exists")
    
    # Create tenant
    tenant = Tenant(
        name=data.name,
        slug=data.slug,
        subdomain=data.subdomain,
        timezone=data.timezone,
        service_area=data.service_area,
        primary_contact_name=data.primary_contact_name,
        primary_contact_email=data.primary_contact_email,
        primary_phone=data.primary_phone,
        booking_mode=data.booking_mode,
        emergency_rules=data.emergency_rules,
        twilio_phone_number=data.twilio_phone_number,
        twilio_messaging_service_sid=data.twilio_messaging_service_sid,
        tone_profile=data.tone_profile,
        sms_signature=data.sms_signature
    )
    
    tenant_dict = tenant.model_dump(mode='json')
    await db.tenants.insert_one(tenant_dict)
    
    # Create owner user
    owner = User(
        email=data.owner_email,
        name=data.owner_name,
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
        tenant_id=tenant.id,
        password_hash=hash_password(data.owner_password)
    )
    
    owner_dict = owner.model_dump(mode='json')
    await db.users.insert_one(owner_dict)
    
    return serialize_doc(tenant_dict)


@v1_router.get("/admin/tenants/{tenant_id}")
async def get_tenant_detail(tenant_id: str, current_user: dict = Depends(require_superadmin)):
    """Get tenant details with summary stats"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get summary stats
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    stats = {
        "leads_total": await db.leads.count_documents({"tenant_id": tenant_id}),
        "leads_last_30d": await db.leads.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": thirty_days_ago.isoformat()}
        }),
        "jobs_total": await db.jobs.count_documents({"tenant_id": tenant_id}),
        "jobs_last_30d": await db.jobs.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": thirty_days_ago.isoformat()}
        }),
        "customers_total": await db.customers.count_documents({"tenant_id": tenant_id}),
        "technicians_total": await db.technicians.count_documents({"tenant_id": tenant_id}),
        "quotes_total": await db.quotes.count_documents({"tenant_id": tenant_id}),
        "invoices_total": await db.invoices.count_documents({"tenant_id": tenant_id}),
        "campaigns_total": await db.campaigns.count_documents({"tenant_id": tenant_id}),
        "conversations_total": await db.conversations.count_documents({"tenant_id": tenant_id}),
        "messages_total": await db.messages.count_documents({"tenant_id": tenant_id}),
    }
    
    return {**serialize_doc(tenant), "stats": stats}


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
    # Voice AI Configuration
    voice_ai_enabled: Optional[bool] = None
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


@v1_router.put("/admin/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, data: TenantUpdate, current_user: dict = Depends(require_superadmin)):
    """Update tenant details"""
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    update_data = {k: v for k, v in data.model_dump(mode='json').items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.tenants.update_one({"id": tenant_id}, {"$set": update_data})
    
    updated = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    return serialize_doc(updated)


@v1_router.delete("/admin/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str, current_user: dict = Depends(require_superadmin)):
    """Delete tenant and ALL associated data"""
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Delete all tenant data
    await db.users.delete_many({"tenant_id": tenant_id})
    await db.customers.delete_many({"tenant_id": tenant_id})
    await db.properties.delete_many({"tenant_id": tenant_id})
    await db.technicians.delete_many({"tenant_id": tenant_id})
    await db.leads.delete_many({"tenant_id": tenant_id})
    await db.jobs.delete_many({"tenant_id": tenant_id})
    await db.quotes.delete_many({"tenant_id": tenant_id})
    await db.invoices.delete_many({"tenant_id": tenant_id})
    await db.conversations.delete_many({"tenant_id": tenant_id})
    await db.messages.delete_many({"tenant_id": tenant_id})
    await db.campaigns.delete_many({"tenant_id": tenant_id})
    await db.campaign_recipients.delete_many({"tenant_id": tenant_id})
    
    # Delete tenant
    await db.tenants.delete_one({"id": tenant_id})
    
    return {"success": True, "message": f"Tenant {tenant['name']} and all data deleted"}


@v1_router.get("/admin/tenants/{tenant_id}/storage")
async def get_tenant_storage(tenant_id: str, current_user: dict = Depends(require_superadmin)):
    """Get detailed storage/data usage for a tenant"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Count documents in each collection
    collections = {
        "users": await db.users.count_documents({"tenant_id": tenant_id}),
        "customers": await db.customers.count_documents({"tenant_id": tenant_id}),
        "properties": await db.properties.count_documents({"tenant_id": tenant_id}),
        "technicians": await db.technicians.count_documents({"tenant_id": tenant_id}),
        "leads": await db.leads.count_documents({"tenant_id": tenant_id}),
        "jobs": await db.jobs.count_documents({"tenant_id": tenant_id}),
        "quotes": await db.quotes.count_documents({"tenant_id": tenant_id}),
        "invoices": await db.invoices.count_documents({"tenant_id": tenant_id}),
        "conversations": await db.conversations.count_documents({"tenant_id": tenant_id}),
        "messages": await db.messages.count_documents({"tenant_id": tenant_id}),
        "campaigns": await db.campaigns.count_documents({"tenant_id": tenant_id}),
        "campaign_recipients": await db.campaign_recipients.count_documents({"tenant_id": tenant_id}),
    }
    
    total_documents = sum(collections.values())
    
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant["name"],
        "collections": collections,
        "total_documents": total_documents,
    }


# ============= TENANT SETTINGS (FOR TENANT OWNERS) =============

@v1_router.get("/settings/tenant")
async def get_tenant_settings(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get current tenant's settings"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Remove sensitive fields for non-superadmin
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        sensitive_fields = ["twilio_auth_token", "twilio_api_key_secret", "openai_api_key", "elevenlabs_api_key"]
        for field in sensitive_fields:
            if field in tenant:
                tenant[field] = "********" if tenant[field] else None
    
    return serialize_doc(tenant)


@v1_router.put("/settings/tenant")
async def update_tenant_settings(
    data: TenantUpdate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update current tenant's settings (owner only)"""
    if current_user.get("role") not in [UserRole.OWNER.value, UserRole.SUPERADMIN.value]:
        raise HTTPException(status_code=403, detail="Only owner can update tenant settings")
    
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    update_data = {k: v for k, v in data.model_dump(mode='json').items() if v is not None}
    
    # Non-superadmins can't update sensitive fields
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        sensitive_fields = ["twilio_account_sid", "twilio_auth_token", "twilio_api_key_sid", 
                          "twilio_api_key_secret", "openai_api_key", "elevenlabs_api_key"]
        for field in sensitive_fields:
            update_data.pop(field, None)
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.tenants.update_one({"id": tenant_id}, {"$set": update_data})
    
    updated = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    return serialize_doc(updated)


# ============= CUSTOMERS ENDPOINTS =============

@v1_router.get("/customers")
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


@v1_router.get("/customers/{customer_id}")
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


@v1_router.post("/customers")
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


@v1_router.put("/customers/{customer_id}")
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


@v1_router.delete("/customers/{customer_id}")
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


@v1_router.post("/customers/bulk-delete")
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


@v1_router.post("/customers/{customer_id}/review-opt-out")
async def customer_review_opt_out(
    customer_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Opt a customer out of automated review requests"""
    result = await db.customers.update_one(
        {"id": customer_id, "tenant_id": tenant_id},
        {"$set": {"review_opt_out": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"success": True}


@v1_router.post("/customers/{customer_id}/review-opt-in")
async def customer_review_opt_in(
    customer_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Re-enable review requests for a customer"""
    result = await db.customers.update_one(
        {"id": customer_id, "tenant_id": tenant_id},
        {"$set": {"review_opt_out": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"success": True}


# ============= PROPERTIES ENDPOINTS =============

@v1_router.get("/properties")
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


@v1_router.post("/properties")
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


@v1_router.put("/properties/{property_id}")
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


# ============= TECHNICIANS ENDPOINTS =============

@v1_router.get("/technicians")
async def list_technicians(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List technicians"""
    techs = await db.technicians.find(
        {"tenant_id": tenant_id}, {"_id": 0}
    ).to_list(100)
    return serialize_docs(techs)


@v1_router.post("/technicians")
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


@v1_router.put("/technicians/{technician_id}")
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


# ============= LEADS ENDPOINTS =============

@v1_router.get("/leads")
async def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    urgency: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List leads with optional filters"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    if source:
        query["source"] = source
    if urgency:
        query["urgency"] = urgency
    
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Enrich leads with customer and property data
    enriched_leads = []
    for lead in leads:
        customer = None
        prop = None
        if lead.get("customer_id"):
            customer = await db.customers.find_one({"id": lead["customer_id"]}, {"_id": 0})
        if lead.get("property_id"):
            prop = await db.properties.find_one({"id": lead["property_id"]}, {"_id": 0})
        
        # Also get address from lead itself if stored there
        address = lead.get("captured_address") or lead.get("address_line1") or (prop.get("address_line1") if prop else None)
        
        enriched_leads.append({
            **serialize_doc(lead),
            "customer": serialize_doc(customer) if customer else None,
            "property": serialize_doc(prop) if prop else None,
            "address": address,
            "caller_name": lead.get("caller_name") or (f"{customer['first_name']} {customer['last_name']}" if customer else "Unknown")
        })
    
    return enriched_leads


@v1_router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get lead with customer and conversation"""
    lead = await db.leads.find_one(
        {"id": lead_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get customer if linked
    customer = None
    if lead.get("customer_id"):
        customer = await db.customers.find_one(
            {"id": lead["customer_id"]}, {"_id": 0}
        )
    
    # Get conversation
    conversation = await db.conversations.find_one(
        {"lead_id": lead_id}, {"_id": 0}
    )
    
    messages = []
    if conversation:
        messages = await db.messages.find(
            {"conversation_id": conversation["id"]}, {"_id": 0}
        ).sort("created_at", 1).to_list(100)
    
    return {
        **serialize_doc(lead),
        "customer": serialize_doc(customer) if customer else None,
        "conversation": serialize_doc(conversation) if conversation else None,
        "messages": serialize_docs(messages)
    }


@v1_router.post("/leads")
async def create_lead(
    data: LeadCreate,
    tenant_id: Optional[str] = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new lead"""
    # For superadmin without tenant_id, require it to be specified
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for lead creation")
    
    lead = Lead(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )
    
    lead_dict = lead.model_dump(mode='json')
    await db.leads.insert_one(lead_dict)
    
    return serialize_doc(lead_dict)


@v1_router.put("/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    data: LeadCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update lead"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["last_activity_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.leads.update_one(
        {"id": lead_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return serialize_doc(lead)


@v1_router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a lead"""
    result = await db.leads.delete_one({"id": lead_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "message": "Lead deleted"}


@v1_router.post("/leads/bulk-delete")
async def bulk_delete_leads(
    lead_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete leads and their associated jobs"""
    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided")
    
    # Delete associated jobs first
    await db.jobs.delete_many({"lead_id": {"$in": lead_ids}, "tenant_id": tenant_id})
    
    # Delete the leads
    result = await db.leads.delete_many({"id": {"$in": lead_ids}, "tenant_id": tenant_id})
    
    return {"success": True, "deleted_count": result.deleted_count}


# ============= JOBS ENDPOINTS =============

@v1_router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List jobs with optional filters"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    if date_from:
        query["service_window_start"] = {"$gte": date_from}
    if date_to:
        if "service_window_start" in query:
            query["service_window_start"]["$lte"] = date_to
        else:
            query["service_window_start"] = {"$lte": date_to}
    
    jobs = await db.jobs.find(query, {"_id": 0}).sort("service_window_start", 1).to_list(1000)
    
    # Enrich with customer and property info
    for job in jobs:
        customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
        prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
        tech = None
        if job.get("assigned_technician_id"):
            tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0})
        
        job["customer"] = serialize_doc(customer) if customer else None
        job["property"] = serialize_doc(prop) if prop else None
        job["technician"] = serialize_doc(tech) if tech else None
    
    return serialize_docs(jobs)


@v1_router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get job details"""
    job = await db.jobs.find_one(
        {"id": job_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
    prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
    tech = None
    if job.get("assigned_technician_id"):
        tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0})
    
    return {
        **serialize_doc(job),
        "customer": serialize_doc(customer) if customer else None,
        "property": serialize_doc(prop) if prop else None,
        "technician": serialize_doc(tech) if tech else None
    }


@v1_router.post("/jobs")
async def create_job(
    data: JobCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new job"""
    # Verify customer and property exist
    customer = await db.customers.find_one({"id": data.customer_id, "tenant_id": tenant_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    prop = await db.properties.find_one({"id": data.property_id, "tenant_id": tenant_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get lead urgency for quote calculation if not already provided
    job_data = data.model_dump(mode='json')
    if not job_data.get("quote_amount") and data.lead_id:
        lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0, "urgency": 1})
        lead_urgency = lead.get("urgency") if lead else None
        job_data["quote_amount"] = calculate_quote_amount(job_data.get("job_type", "DIAGNOSTIC"), lead_urgency)
    elif not job_data.get("quote_amount"):
        # Calculate based on job type and priority
        priority_to_urgency = {"EMERGENCY": "EMERGENCY", "HIGH": "URGENT", "NORMAL": "ROUTINE"}
        urgency = priority_to_urgency.get(job_data.get("priority", "NORMAL"), "ROUTINE")
        job_data["quote_amount"] = calculate_quote_amount(job_data.get("job_type", "DIAGNOSTIC"), urgency)
    
    job = Job(
        tenant_id=tenant_id,
        **job_data
    )
    
    job_dict = job.model_dump(mode='json')
    await db.jobs.insert_one(job_dict)
    
    # Create a Quote record linked to the job (if quote_amount exists)
    if job_dict.get("quote_amount"):
        lead_data = None
        if data.lead_id:
            lead_data = await db.leads.find_one({"id": data.lead_id}, {"_id": 0})
        
        quote_description = f"{job_dict.get('job_type', 'Service')} service"
        if lead_data:
            if lead_data.get("issue_type"):
                quote_description = f"{job_dict.get('job_type')} - {lead_data.get('issue_type')}"
            if lead_data.get("description"):
                quote_description += f"\n{lead_data.get('description')}"
        
        quote = Quote(
            tenant_id=tenant_id,
            customer_id=data.customer_id,
            property_id=data.property_id,
            job_id=job.id,
            amount=job_dict["quote_amount"],
            description=quote_description,
            status=QuoteStatus.SENT
        )
        
        quote_dict = quote.model_dump(mode='json')
        quote_dict["sent_at"] = datetime.now(timezone.utc).isoformat()
        await db.quotes.insert_one(quote_dict)
        
        # Link quote to job
        job_dict["quote_id"] = quote.id
        await db.jobs.update_one(
            {"id": job.id},
            {"$set": {"quote_id": quote.id}}
        )
        
        # Send quote SMS to customer
        tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
        if tenant and tenant.get("twilio_phone_number"):
            from services.twilio_service import twilio_service
            
            # Send quote SMS (continuation, no greeting)
            sms_sig = tenant.get('sms_signature', '').strip()
            quote_message = f"Your service quote for {job_dict.get('job_type', 'service')} is ${job_dict['quote_amount']:.2f}. Pay securely here: [YOUR PAYMENT LINK HERE]. Reply with any questions!{' ' + sms_sig if sms_sig else ''}"
            
            await twilio_service.send_sms(
                to_phone=customer["phone"],
                body=quote_message,
                from_phone=tenant["twilio_phone_number"]
            )
    
    # Update lead status if linked
    if data.lead_id:
        await db.leads.update_one(
            {"id": data.lead_id, "tenant_id": tenant_id},
            {"$set": {"status": LeadStatus.JOB_BOOKED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    return serialize_doc(job_dict)


@v1_router.put("/jobs/{job_id}")
async def update_job(
    job_id: str,
    data: JobCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update job"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["service_window_start"] = update_data["service_window_start"].isoformat()
    update_data["service_window_end"] = update_data["service_window_end"].isoformat()
    if update_data.get("exact_arrival_time"):
        update_data["exact_arrival_time"] = update_data["exact_arrival_time"].isoformat()
    
    result = await db.jobs.update_one(
        {"id": job_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return serialize_doc(job)


class EnRouteRequest(BaseModel):
    technician_id: Optional[str] = None
    estimated_minutes: int = 30
    send_sms: bool = True
    include_tracking_link: bool = True


@v1_router.post("/jobs/{job_id}/en-route")
async def mark_job_en_route(
    job_id: str,
    data: EnRouteRequest = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Mark job as en-route, generate tracking token, and send SMS"""
    import secrets as _sec
    if data is None:
        data = EnRouteRequest()
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tracking_token = _sec.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    estimated_arrival = (now + timedelta(minutes=data.estimated_minutes)).isoformat()
    tech_id = data.technician_id or job.get("assigned_technician_id")

    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": JobStatus.EN_ROUTE.value,
            "en_route_at": now.isoformat(),
            "en_route_sms_sent": True,
            "tracking_token": tracking_token,
            "estimated_arrival": estimated_arrival,
            "assigned_technician_id": tech_id,
            "updated_at": now.isoformat()
        }}
    )
    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    sms_sent = False

    if data.send_sms and customer and tenant and tenant.get("twilio_phone_number"):
        from services.twilio_service import twilio_service
        tech = None
        if tech_id:
            tech = await db.technicians.find_one({"id": tech_id}, {"_id": 0})
        tech_name = (tech.get("name") if tech else None) or "Your technician"
        eta_time = (now + timedelta(minutes=data.estimated_minutes)).strftime("%-I:%M %p")
        message = (
            f"Hi {customer.get('first_name', 'there')}! "
            f"{tech_name} from {tenant['name']} is on the way. "
            f"Estimated arrival: {eta_time} (~{data.estimated_minutes} min)."
        )
        if data.include_tracking_link:
            base_url = tenant.get("app_url", "https://app.fieldos.com")
            message += f" Track: {base_url}/track/{tracking_token}"
        if tenant.get("sms_signature"):
            message += f" {tenant['sms_signature']}"
        result = await twilio_service.send_sms(
            to_phone=customer["phone"],
            body=message,
            from_phone=tenant["twilio_phone_number"]
        )
        sms_sent = result.get("success", False)
        if sms_sent:
            msg = Message(
                tenant_id=tenant_id,
                conversation_id="",
                customer_id=customer["id"],
                direction=MessageDirection.OUTBOUND,
                sender_type=SenderType.SYSTEM,
                content=message,
                metadata={"twilio_sid": result.get("provider_message_id")}
            )
            await db.messages.insert_one(msg.model_dump(mode='json'))

    return {"success": True, "sms_sent": sms_sent, "tracking_token": tracking_token}


@v1_router.post("/jobs/{job_id}/arrived")
async def mark_job_arrived(
    job_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Mark technician as arrived on site"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    now = datetime.now(timezone.utc)
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": JobStatus.IN_PROGRESS.value,
            "actual_arrival": now.isoformat(),
            "updated_at": now.isoformat()
        }}
    )
    return {"success": True, "arrived_at": now.isoformat()}


class _CompletionPhoto(BaseModel):
    type: str = "OTHER"
    url: str
    caption: Optional[str] = None


class _AdditionalCharge(BaseModel):
    description: str
    amount: float


class JobCompleteRequest(BaseModel):
    technician_id: Optional[str] = None
    completion_notes: Optional[str] = None
    photos: Optional[List[_CompletionPhoto]] = None
    signature_url: Optional[str] = None
    additional_charges: Optional[List[_AdditionalCharge]] = None
    send_invoice: bool = True
    request_review: bool = True


@v1_router.post("/jobs/{job_id}/complete")
async def complete_job(
    job_id: str,
    data: JobCompleteRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Complete job: mark done, auto-create invoice, send payment SMS, schedule review"""
    import secrets as _sec
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    now = datetime.now(timezone.utc)

    update_fields = {"status": JobStatus.COMPLETED.value, "completed_at": now.isoformat(), "updated_at": now.isoformat()}
    if data.completion_notes:
        update_fields["completion_notes"] = data.completion_notes
    if data.photos:
        update_fields["completion_photos"] = [p.model_dump() for p in data.photos]
    if data.signature_url:
        update_fields["signature_url"] = data.signature_url
    if data.technician_id:
        update_fields["assigned_technician_id"] = data.technician_id
    await db.jobs.update_one({"id": job_id}, {"$set": update_fields})

    invoice_doc = None
    invoice_sent = False

    if data.send_invoice and customer:
        existing = await db.invoices.find_one({"job_id": job_id, "tenant_id": tenant_id})
        if not existing:
            line_items = []
            base_amount = job.get("quote_amount", 0) or 0
            if base_amount:
                line_items.append({
                    "description": f"{job.get('job_type', 'Service')} - {data.completion_notes or 'Service completed'}",
                    "quantity": 1, "unit_price": base_amount, "total": base_amount, "type": "LABOR"
                })
            for charge in (data.additional_charges or []):
                line_items.append({"description": charge.description, "quantity": 1,
                                   "unit_price": charge.amount, "total": charge.amount, "type": "FEE"})
            subtotal = sum(i["total"] for i in line_items)
            inv_settings = (tenant.get("invoice_settings") or {}) if tenant else {}
            tax_rate = inv_settings.get("default_tax_rate", 0)
            tax_amount = round(subtotal * tax_rate / 100, 2)
            total = round(subtotal + tax_amount, 2)
            next_num = inv_settings.get("next_invoice_number", 1)
            prefix = inv_settings.get("invoice_prefix", "INV")
            invoice_number = f"{prefix}-{now.year}-{next_num:04d}"
            await db.tenants.update_one({"id": tenant_id}, {"$set": {"invoice_settings.next_invoice_number": next_num + 1}})
            due_date = (now + timedelta(days=inv_settings.get("default_payment_terms", 10))).date().isoformat()
            payment_token = _sec.token_urlsafe(16)
            invoice_doc = {
                "id": str(uuid4()), "tenant_id": tenant_id,
                "customer_id": job["customer_id"], "property_id": job.get("property_id"),
                "job_id": job_id, "quote_id": job.get("quote_id"),
                "invoice_number": invoice_number, "line_items": line_items,
                "subtotal": subtotal, "discount_type": None, "discount_value": 0, "discount_amount": 0,
                "tax_rate": tax_rate, "tax_amount": tax_amount, "total": total,
                "amount_paid": 0, "amount_due": total, "status": "SENT",
                "invoice_date": now.isoformat(), "due_date": due_date, "sent_at": now.isoformat(),
                "payment_link_token": payment_token, "payments": [],
                "notes": inv_settings.get("invoice_footer_text", ""),
                "created_at": now.isoformat(), "updated_at": now.isoformat(),
            }
            await db.invoices.insert_one(invoice_doc)
            await db.jobs.update_one({"id": job_id}, {"$set": {"invoice_id": invoice_doc["id"]}})

            if tenant and tenant.get("twilio_phone_number") and customer.get("phone"):
                from services.twilio_service import twilio_service
                base_url = tenant.get("app_url", "https://app.fieldos.com")
                payment_link = f"{base_url}/pay/{payment_token}"
                notes_line = f"\nSummary: {data.completion_notes}" if data.completion_notes else ""
                msg_body = (
                    f"Hi {customer.get('first_name', 'there')}! "
                    f"Your {job.get('job_type', 'service')} is complete.{notes_line}\n"
                    f"Invoice #{invoice_number}: ${total:.2f}\n"
                    f"Pay securely: {payment_link}"
                )
                if tenant.get("sms_signature"):
                    msg_body += f" {tenant['sms_signature']}"
                res = await twilio_service.send_sms(
                    to_phone=customer["phone"], body=msg_body, from_phone=tenant["twilio_phone_number"]
                )
                invoice_sent = res.get("success", False)

    review_scheduled_at = None
    if data.request_review and tenant:
        review_settings = tenant.get("review_settings") or {}
        delay_hours = review_settings.get("delay_hours", 2)
        review_scheduled_at = (now + timedelta(hours=delay_hours)).isoformat()
        await db.jobs.update_one({"id": job_id}, {"$set": {"review_scheduled_at": review_scheduled_at}})

    updated_job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return {
        "success": True,
        "job": serialize_doc(updated_job),
        "invoice": serialize_doc(invoice_doc) if invoice_doc else None,
        "invoice_sent": invoice_sent,
        "review_scheduled": review_scheduled_at is not None,
        "review_send_at": review_scheduled_at,
    }


class OnMyWayRequest(BaseModel):
    eta_minutes: int = 30
    custom_message: Optional[str] = None


@v1_router.post("/jobs/{job_id}/on-my-way")
async def send_on_my_way(
    job_id: str,
    data: OnMyWayRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send 'On My Way' SMS with custom ETA"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured")
    tech = await db.technicians.find_one({"id": job.get("assigned_technician_id")}, {"_id": 0}) if job.get("assigned_technician_id") else None
    tech_name = tech.get("name", "Your technician") if tech else "Your technician"
    if data.custom_message:
        message = data.custom_message
    else:
        message = f"Hi {customer.get('first_name', 'there')}! {tech_name} from {tenant['name']} is on the way and will arrive in approximately {data.eta_minutes} minutes."
        if tenant.get("sms_signature"):
            message += f" {tenant['sms_signature']}"
    from services.twilio_service import twilio_service
    await twilio_service.send_sms(to_phone=customer["phone"], body=message, from_phone=tenant["twilio_phone_number"])
    await db.jobs.update_one({"id": job_id}, {"$set": {"status": JobStatus.EN_ROUTE.value, "en_route_at": datetime.now(timezone.utc).isoformat(), "eta_minutes": data.eta_minutes}})
    return {"success": True, "message": "On My Way notification sent"}


class ReviewRequestPayload(BaseModel):
    platform: str = "google"


@v1_router.post("/jobs/{job_id}/request-review")
async def request_review(
    job_id: str,
    data: ReviewRequestPayload,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send review request SMS after job completion"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != JobStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Job must be completed")
    customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured")
    review_settings = tenant.get("review_settings") or {}
    branding = tenant.get("branding") or {}
    review_urls = {
        "google": review_settings.get("google_review_url") or branding.get("google_review_url", ""),
        "yelp": review_settings.get("yelp_review_url") or branding.get("yelp_review_url", ""),
        "facebook": review_settings.get("facebook_review_url") or branding.get("facebook_review_url", ""),
    }
    review_url = review_urls.get(data.platform, "")
    message = f"Hi {customer.get('first_name', 'there')}! Thank you for choosing {tenant['name']}. We hope you're satisfied with our service!"
    if review_url:
        message += f" We'd love your feedback: {review_url}"
    if tenant.get("sms_signature"):
        message += f" {tenant['sms_signature']}"
    from services.twilio_service import twilio_service
    await twilio_service.send_sms(to_phone=customer["phone"], body=message, from_phone=tenant["twilio_phone_number"])
    await db.jobs.update_one({"id": job_id}, {"$set": {
        "review_requested_at": datetime.now(timezone.utc).isoformat(),
        "review_platform": data.platform,
        "review_request_sent": True,
    }})
    return {"success": True, "message": "Review request sent"}


@v1_router.post("/jobs/bulk-delete")
async def bulk_delete_jobs(
    job_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete jobs"""
    if not job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    
    result = await db.jobs.delete_many({"id": {"$in": job_ids}, "tenant_id": tenant_id})
    
    return {"success": True, "deleted_count": result.deleted_count}


# ============= QUOTES ENDPOINTS =============

@v1_router.get("/quotes")
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


@v1_router.post("/quotes")
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


@v1_router.put("/quotes/{quote_id}")
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


class ConvertToInvoiceRequest(BaseModel):
    due_date: Optional[str] = None
    send_immediately: bool = False


@v1_router.post("/quotes/{quote_id}/convert-to-invoice")
async def convert_quote_to_invoice(
    quote_id: str,
    data: ConvertToInvoiceRequest = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Convert a quote to an invoice"""
    if data is None:
        data = ConvertToInvoiceRequest()
    quote = await db.quotes.find_one({"id": quote_id, "tenant_id": tenant_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    due_date = data.due_date if data.due_date else (now + timedelta(days=30)).strftime("%Y-%m-%d")
    send_immediately = data.send_immediately
    # Generate invoice number
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    invoice_settings = (tenant or {}).get("invoice_settings") or {}
    next_num = invoice_settings.get("next_invoice_number", 1)
    prefix = invoice_settings.get("invoice_prefix", "INV")
    current_year = now.year
    invoice_number = f"{prefix}-{current_year}-{next_num:04d}"
    # Increment counter
    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {"invoice_settings.next_invoice_number": next_num + 1}}
    )
    # Create invoice
    invoice_id = str(uuid4())
    invoice_doc = {
        "id": invoice_id,
        "tenant_id": tenant_id,
        "customer_id": quote.get("customer_id", ""),
        "job_id": quote.get("job_id") or "",
        "amount": quote.get("amount", 0),
        "currency": "USD",
        "status": InvoiceStatus.SENT.value if send_immediately else InvoiceStatus.DRAFT.value,
        "due_date": due_date,
        "invoice_number": invoice_number,
        "quote_id": quote_id,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await db.invoices.insert_one(invoice_doc)
    # Send SMS if requested
    if send_immediately:
        customer = await db.customers.find_one({"id": invoice_doc["customer_id"]}, {"_id": 0})
        if customer and customer.get("phone") and tenant and tenant.get("twilio_phone_number"):
            name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or customer.get("name", "there")
            company = tenant.get("name", "Us")
            amount = invoice_doc["amount"]
            payment_link = invoice_doc.get("stripe_payment_link", "")
            if payment_link:
                message = f"Hi {name}! Invoice #{invoice_number} from {company} for ${amount:.2f} is ready. {payment_link}"
            else:
                message = f"Hi {name}! Invoice #{invoice_number} from {company} for ${amount:.2f} is ready. Please call us to arrange payment."
            try:
                from services.twilio_service import twilio_service
                await twilio_service.send_sms(to_phone=customer["phone"], body=message, from_phone=tenant["twilio_phone_number"])
                await db.invoices.update_one({"id": invoice_id}, {"$set": {"sent_at": now_iso}})
                invoice_doc["sent_at"] = now_iso
            except Exception:
                pass
    # Remove _id for response
    invoice_doc.pop("_id", None)
    return serialize_doc(invoice_doc)



# ============= INVOICES ENDPOINTS =============

@v1_router.get("/invoices")
async def list_invoices(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List invoices with optional filters"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    if customer_id:
        query["customer_id"] = customer_id
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for invoice in invoices:
        customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})
        job = await db.jobs.find_one({"id": invoice.get("job_id")}, {"_id": 0})
        invoice["customer"] = serialize_doc(customer) if customer else None
        invoice["job"] = serialize_doc(job) if job else None
    
    return serialize_docs(invoices)


@v1_router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get invoice details"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})
    job = await db.jobs.find_one({"id": invoice.get("job_id")}, {"_id": 0})
    
    return {
        **serialize_doc(invoice),
        "customer": serialize_doc(customer) if customer else None,
        "job": serialize_doc(job) if job else None
    }


@v1_router.post("/invoices")
async def create_invoice(
    data: InvoiceCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new invoice"""
    # Verify customer exists
    customer = await db.customers.find_one({"id": data.customer_id, "tenant_id": tenant_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Verify job exists
    job = await db.jobs.find_one({"id": data.job_id, "tenant_id": tenant_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    invoice = Invoice(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )
    
    invoice_dict = invoice.model_dump(mode='json')
    await db.invoices.insert_one(invoice_dict)
    
    return serialize_doc(invoice_dict)


@v1_router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    data: InvoiceCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update invoice"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    return serialize_doc(invoice)


@v1_router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Mark invoice as paid"""
    result = await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": {
            "status": InvoiceStatus.PAID.value,
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {"success": True, "message": "Invoice marked as paid"}


@v1_router.post("/invoices/{invoice_id}/send")
async def send_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send invoice via SMS"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured")
    name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or customer.get("name", "there")
    company = tenant.get("name", "Us")
    number = invoice.get("invoice_number", f"INV-{invoice_id[:6].upper()}")
    amount = invoice.get("amount", 0)
    payment_link = invoice.get("stripe_payment_link", "")
    if payment_link:
        message = f"Hi {name}! Invoice #{number} from {company} for ${amount:.2f} is ready. {payment_link}"
    else:
        message = f"Hi {name}! Invoice #{number} from {company} for ${amount:.2f} is ready. Please call us to arrange payment."
    from services.twilio_service import twilio_service
    await twilio_service.send_sms(to_phone=customer["phone"], body=message, from_phone=tenant["twilio_phone_number"])
    now = datetime.now(timezone.utc).isoformat()
    await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": {"status": InvoiceStatus.SENT.value, "sent_at": now, "updated_at": now}}
    )
    return {"success": True}


@v1_router.post("/invoices/{invoice_id}/remind")
async def remind_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send invoice reminder via SMS"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("status") in [InvoiceStatus.PAID.value, "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Cannot send reminder for paid or cancelled invoice")
    customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})
    if not customer or not customer.get("phone"):
        raise HTTPException(status_code=400, detail="Customer phone not found")
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="SMS not configured")
    name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or customer.get("name", "there")
    company = tenant.get("name", "Us")
    number = invoice.get("invoice_number", f"INV-{invoice_id[:6].upper()}")
    amount = invoice.get("amount", 0)
    payment_link = invoice.get("stripe_payment_link", "")
    if payment_link:
        message = f"Friendly reminder: Invoice #{number} from {company} for ${amount:.2f} is still outstanding. {payment_link}"
    else:
        message = f"Friendly reminder: Invoice #{number} from {company} for ${amount:.2f} is still outstanding. Please call us to arrange payment."
    from services.twilio_service import twilio_service
    await twilio_service.send_sms(to_phone=customer["phone"], body=message, from_phone=tenant["twilio_phone_number"])
    now = datetime.now(timezone.utc).isoformat()
    reminder_count = invoice.get("reminder_count", 0) + 1
    await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": {"reminder_count": reminder_count, "last_reminder_at": now, "updated_at": now}}
    )
    return {"success": True}


class RecordPaymentRequest(BaseModel):
    amount: float
    method: Optional[str] = "CASH"
    notes: Optional[str] = ""


@v1_router.post("/invoices/{invoice_id}/record-payment")
async def record_invoice_payment(
    invoice_id: str,
    data: RecordPaymentRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Record a payment against an invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    now = datetime.now(timezone.utc).isoformat()
    payment_entry = {
        "amount": data.amount,
        "method": data.method or "CASH",
        "notes": data.notes or "",
        "recorded_at": now
    }
    payments = invoice.get("payments", [])
    payments.append(payment_entry)
    amount_paid = sum(p.get("amount", 0) for p in payments)
    invoice_total = invoice.get("amount", 0)
    amount_due = invoice_total - amount_paid
    update_fields = {
        "payments": payments,
        "amount_paid": amount_paid,
        "amount_due": max(amount_due, 0),
        "updated_at": now
    }
    if amount_due <= 0:
        update_fields["status"] = InvoiceStatus.PAID.value
        update_fields["paid_at"] = now
    else:
        update_fields["status"] = InvoiceStatus.PARTIALLY_PAID.value
    await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": update_fields}
    )
    updated = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    return serialize_doc(updated)


@v1_router.post("/invoices/{invoice_id}/void")
async def void_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Void an invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("status") == InvoiceStatus.PAID.value:
        raise HTTPException(status_code=400, detail="Cannot void a paid invoice")
    now = datetime.now(timezone.utc).isoformat()
    await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": {"status": "CANCELLED", "voided_at": now, "updated_at": now}}
    )
    return {"success": True}


@v1_router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a draft invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("status") != InvoiceStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Only DRAFT invoices can be deleted")
    await db.invoices.delete_one({"id": invoice_id, "tenant_id": tenant_id})
    return {"success": True}



@v1_router.get("/invoices/public/{token}")
async def get_invoice_by_token(token: str):
    """
    Public endpoint — no auth required.
    Returns invoice data for the customer-facing /pay/:token page.
    """
    invoice = await db.invoices.find_one({"payment_link_token": token}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found or link has expired")

    tenant = await db.tenants.find_one({"id": invoice.get("tenant_id")}, {"_id": 0})
    customer = await db.customers.find_one({"id": invoice.get("customer_id")}, {"_id": 0})

    cust_name = ""
    if customer:
        cust_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or customer.get("name", "")

    company_info = {
        "name": (tenant or {}).get("name", "FieldOS"),
        "logo_url": ((tenant or {}).get("branding") or {}).get("logo_url"),
        "primary_color": ((tenant or {}).get("branding") or {}).get("primary_color", "#0066CC"),
        "phone": (tenant or {}).get("primary_phone"),
    }

    return {
        "id": invoice["id"],
        "invoice_number": invoice.get("invoice_number", f"INV-{invoice['id'][:6].upper()}"),
        "amount": invoice.get("amount", 0),
        "status": invoice.get("status", "SENT"),
        "due_date": invoice.get("due_date"),
        "notes": invoice.get("notes", ""),
        "stripe_payment_link": invoice.get("stripe_payment_link"),
        "paid_at": invoice.get("paid_at"),
        "customer": {"name": cust_name} if cust_name else None,
        "company": company_info,
    }


# ============= INVOICE SETTINGS =============

@v1_router.get("/settings/invoice")
async def get_invoice_settings(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get invoice settings"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    settings = tenant.get("invoice_settings") or {}
    stripe_key = tenant.get("stripe_secret_key", "")
    if stripe_key and len(stripe_key) > 8:
        stripe_key = stripe_key[:7] + "..." + stripe_key[-4:]
    return {**settings, "stripe_secret_key": stripe_key, "stripe_configured": bool(tenant.get("stripe_secret_key"))}


@v1_router.put("/settings/invoice")
async def update_invoice_settings(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update invoice settings"""
    stripe_key = data.pop("stripe_secret_key", None)
    set_data = {f"invoice_settings.{k}": v for k, v in data.items()
                if k not in ("stripe_configured",) and v is not None}
    if stripe_key and "..." not in stripe_key and len(stripe_key) > 10:
        set_data["stripe_secret_key"] = stripe_key
    set_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.tenants.update_one({"id": tenant_id}, {"$set": set_data})
    return {"success": True}


# ============= VOICE AI SETTINGS =============

VOICE_FIELDS = [
    "voice_ai_enabled", "elevenlabs_api_key", "elevenlabs_voice_id",
    "voice_provider", "voice_model", "voice_name", "voice_greeting",
    "voice_system_prompt", "voice_collect_fields", "voice_business_hours",
    "voice_after_hours_message",
]

@v1_router.get("/settings/voice")
async def get_voice_settings(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get voice AI settings"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    settings = {f: tenant.get(f) for f in VOICE_FIELDS}
    # Mask ElevenLabs API key
    key = settings.get("elevenlabs_api_key", "")
    if key and len(key) > 8:
        settings["elevenlabs_api_key_masked"] = key[:4] + "..." + key[-4:]
        settings["elevenlabs_configured"] = True
    else:
        settings["elevenlabs_api_key_masked"] = ""
        settings["elevenlabs_configured"] = False
    settings["elevenlabs_api_key"] = ""  # never return plaintext key
    return settings


@v1_router.put("/settings/voice")
async def update_voice_settings(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update voice AI settings"""
    allowed = set(VOICE_FIELDS)
    set_data = {}
    for k, v in data.items():
        if k not in allowed:
            continue
        # Don't overwrite the real key with a masked value or empty
        if k == "elevenlabs_api_key":
            if not v or "..." in str(v):
                continue
        set_data[k] = v
    if not set_data:
        return {"success": True}
    set_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.tenants.update_one({"id": tenant_id}, {"$set": set_data})
    return {"success": True}


# ============= CONVERSATIONS & MESSAGES =============

@v1_router.get("/conversations")
async def list_conversations(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List conversations"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    
    conversations = await db.conversations.find(query, {"_id": 0}).sort("last_message_at", -1).to_list(100)
    
    for conv in conversations:
        customer = await db.customers.find_one({"id": conv.get("customer_id")}, {"_id": 0})
        conv["customer"] = serialize_doc(customer) if customer else None
    
    return serialize_docs(conversations)


@v1_router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get conversation with messages"""
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await db.messages.find(
        {"conversation_id": conversation_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    customer = await db.customers.find_one({"id": conv.get("customer_id")}, {"_id": 0})
    
    return {
        **serialize_doc(conv),
        "customer": serialize_doc(customer) if customer else None,
        "messages": serialize_docs(messages)
    }


@v1_router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get messages for a conversation"""
    conv = await db.conversations.find_one(
        {"id": conversation_id, "tenant_id": tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await db.messages.find(
        {"conversation_id": conversation_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    return serialize_docs(messages)


@v1_router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation and all its messages"""
    # Delete messages first
    await db.messages.delete_many({"conversation_id": conversation_id, "tenant_id": tenant_id})
    # Delete conversation
    result = await db.conversations.delete_one({"id": conversation_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "message": "Conversation deleted"}


@v1_router.post("/conversations/bulk-delete")
async def bulk_delete_conversations(
    conversation_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete conversations and their messages"""
    if not conversation_ids:
        raise HTTPException(status_code=400, detail="No conversation IDs provided")
    
    # Delete messages
    await db.messages.delete_many({"conversation_id": {"$in": conversation_ids}, "tenant_id": tenant_id})
    # Delete conversations
    result = await db.conversations.delete_many({"id": {"$in": conversation_ids}, "tenant_id": tenant_id})
    return {"success": True, "deleted_count": result.deleted_count}


@v1_router.post("/messages")
async def send_message(
    data: MessageCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send a message (staff sending from UI)"""
    # Verify conversation exists
    conv = await db.conversations.find_one(
        {"id": data.conversation_id, "tenant_id": tenant_id}
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get customer and tenant
    customer = await db.customers.find_one({"id": data.customer_id}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    
    # Send SMS via Twilio if channel is SMS
    twilio_result = None
    if data.channel == PreferredChannel.SMS and customer and tenant and tenant.get("twilio_phone_number"):
        from services.twilio_service import twilio_service
        
        twilio_result = await twilio_service.send_sms(
            to_phone=customer["phone"],
            body=data.content,
            from_phone=tenant["twilio_phone_number"]
        )
    
    # Create message record
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=data.conversation_id,
        customer_id=data.customer_id,
        lead_id=data.lead_id,
        direction=MessageDirection.OUTBOUND,
        sender_type=SenderType.STAFF,
        channel=data.channel,
        content=data.content,
        metadata={"twilio_sid": twilio_result.get("provider_message_id") if twilio_result else None}
    )
    
    msg_dict = msg.model_dump(mode='json')
    await db.messages.insert_one(msg_dict)
    
    # Update conversation
    await db.conversations.update_one(
        {"id": data.conversation_id},
        {"$set": {
            "last_message_from": SenderType.STAFF.value,
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return serialize_doc(msg_dict)


# ============= CAMPAIGNS ENDPOINTS =============

@v1_router.get("/campaigns")
async def list_campaigns(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List campaigns"""
    campaigns = await db.campaigns.find(
        {"tenant_id": tenant_id}, {"_id": 0}
    ).to_list(100)
    return serialize_docs(campaigns)


@v1_router.post("/campaigns")
async def create_campaign(
    data: CampaignCreate,
    tenant_id: Optional[str] = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new campaign"""
    # For superadmin without tenant_id, require it to be specified
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for campaign creation")
    
    campaign = Campaign(
        tenant_id=tenant_id,
        **data.model_dump(mode='json')
    )
    
    campaign_dict = campaign.model_dump(mode='json')
    await db.campaigns.insert_one(campaign_dict)
    
    return serialize_doc(campaign_dict)


@v1_router.put("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: CampaignCreate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update campaign"""
    update_data = data.model_dump(mode='json')
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.campaigns.update_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return serialize_doc(campaign)


@v1_router.post("/campaigns/{campaign_id}/preview-segment")
async def preview_campaign_segment(
    campaign_id: str,
    segment: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Preview customers matching segment criteria.
    segment can include:
    - last_service_days_ago: ">90", ">180", etc.
    - service_type: "HVAC", "Plumbing", etc.
    - customer_status: "active", "inactive"
    """
    import pytz
    
    # Get tenant timezone
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")
    
    now = datetime.now(tenant_tz)
    
    # Build query based on segment
    customer_ids = set()
    
    # Get customers based on last service date
    last_service_days = segment.get("last_service_days_ago", "")
    if last_service_days:
        # Parse ">90", ">180", etc.
        try:
            days = int(last_service_days.replace(">", "").replace("<", "").strip())
            cutoff_date = now - timedelta(days=days)
            
            # Find customers with jobs completed before cutoff
            if last_service_days.startswith(">"):
                # Last service MORE than X days ago
                pipeline = [
                    {"$match": {"tenant_id": tenant_id, "status": "COMPLETED"}},
                    {"$sort": {"service_window_start": -1}},
                    {"$group": {
                        "_id": "$customer_id",
                        "last_service": {"$first": "$service_window_start"}
                    }},
                    {"$match": {"last_service": {"$lt": cutoff_date.isoformat()}}}
                ]
            else:
                # Last service LESS than X days ago
                pipeline = [
                    {"$match": {"tenant_id": tenant_id, "status": "COMPLETED"}},
                    {"$sort": {"service_window_start": -1}},
                    {"$group": {
                        "_id": "$customer_id",
                        "last_service": {"$first": "$service_window_start"}
                    }},
                    {"$match": {"last_service": {"$gte": cutoff_date.isoformat()}}}
                ]
            
            async for doc in db.jobs.aggregate(pipeline):
                if doc["_id"]:
                    customer_ids.add(doc["_id"])
        except:
            pass
    
    # If no service filter, get all customers with at least one completed job
    if not last_service_days:
        jobs = await db.jobs.distinct("customer_id", {"tenant_id": tenant_id, "status": "COMPLETED"})
        customer_ids = set(jobs)
    
    # Get customer details
    if not customer_ids:
        # Fallback: get all customers if no filter matched
        customers = await db.customers.find(
            {"tenant_id": tenant_id},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1}
        ).to_list(500)
    else:
        customers = await db.customers.find(
            {"tenant_id": tenant_id, "id": {"$in": list(customer_ids)}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "phone": 1, "email": 1}
        ).to_list(500)
    
    # Filter out customers without phone numbers
    customers_with_phone = [c for c in customers if c.get("phone")]
    
    return {
        "total_matching": len(customers_with_phone),
        "sample_customers": customers_with_phone[:10],  # Return first 10 as preview
        "segment_applied": segment
    }


@v1_router.post("/campaigns/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Start a campaign: query matching customers, create recipients, and begin sending.
    """
    import pytz
    from services.twilio_service import twilio_service
    
    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] not in ["DRAFT", "PAUSED"]:
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign['status']}")
    
    # Get tenant for Twilio config
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="Tenant Twilio configuration missing")
    
    tenant_tz_str = tenant.get("timezone", "America/New_York")
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")
    
    now = datetime.now(tenant_tz)
    segment = campaign.get("segment_definition") or {}
    
    # Build recipient list based on segment
    customer_ids = set()
    
    last_service_days = segment.get("last_service_days_ago") or segment.get("lastServiceDaysAgo", "")
    if last_service_days:
        try:
            days = int(str(last_service_days).replace(">", "").replace("<", "").strip())
            cutoff_date = now - timedelta(days=days)
            
            pipeline = [
                {"$match": {"tenant_id": tenant_id, "status": "COMPLETED"}},
                {"$sort": {"service_window_start": -1}},
                {"$group": {
                    "_id": "$customer_id",
                    "last_service": {"$first": "$service_window_start"}
                }},
                {"$match": {"last_service": {"$lt": cutoff_date.isoformat()}}}
            ]
            
            async for doc in db.jobs.aggregate(pipeline):
                if doc["_id"]:
                    customer_ids.add(doc["_id"])
        except:
            pass
    
    # If no segment or empty results, get all customers with completed jobs
    if not customer_ids:
        jobs = await db.jobs.distinct("customer_id", {"tenant_id": tenant_id, "status": "COMPLETED"})
        customer_ids = set(jobs) if jobs else set()
    
    # If still empty, get all customers
    if not customer_ids:
        all_customers = await db.customers.find(
            {"tenant_id": tenant_id},
            {"_id": 0, "id": 1}
        ).to_list(500)
        customer_ids = set(c["id"] for c in all_customers)
    
    # Get customer details and create recipients
    customers = await db.customers.find(
        {"tenant_id": tenant_id, "id": {"$in": list(customer_ids)}},
        {"_id": 0}
    ).to_list(500)
    
    # Filter customers with phone numbers
    customers_with_phone = [c for c in customers if c.get("phone")]
    
    # Delete existing recipients for this campaign (in case of restart)
    await db.campaign_recipients.delete_many({"campaign_id": campaign_id})
    
    # Create recipient records
    recipients_created = 0
    for customer in customers_with_phone:
        recipient = CampaignRecipient(
            campaign_id=campaign_id,
            customer_id=customer["id"],
            status=RecipientStatus.PENDING
        )
        recipient_dict = recipient.model_dump(mode='json')
        await db.campaign_recipients.insert_one(recipient_dict)
        recipients_created += 1
    
    # Update campaign status
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": CampaignStatus.RUNNING.value,
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "total_recipients": recipients_created
        }}
    )
    
    return {
        "status": "started",
        "campaign_id": campaign_id,
        "recipients_created": recipients_created,
        "message": f"Campaign started with {recipients_created} recipients. Messages will be sent in batches."
    }


@v1_router.post("/campaigns/{campaign_id}/send-batch")
async def send_campaign_batch(
    campaign_id: str,
    batch_size: int = 10,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a batch of campaign messages. Call repeatedly to send all messages.
    """
    from services.twilio_service import twilio_service
    
    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] != "RUNNING":
        raise HTTPException(status_code=400, detail="Campaign is not running")
    
    # Get tenant for Twilio
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant or not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="Tenant Twilio configuration missing")
    
    from_phone = tenant["twilio_phone_number"]
    message_template = campaign.get("message_template", "")
    
    # Get pending recipients
    pending_recipients = await db.campaign_recipients.find(
        {"campaign_id": campaign_id, "status": RecipientStatus.PENDING.value}
    ).to_list(batch_size)
    
    if not pending_recipients:
        # Mark campaign as completed if no more pending
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {"status": CampaignStatus.COMPLETED.value, "completed_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"status": "completed", "sent_in_batch": 0, "remaining": 0}
    
    sent_count = 0
    errors = []
    
    for recipient in pending_recipients:
        # Get customer
        customer = await db.customers.find_one(
            {"id": recipient["customer_id"]},
            {"_id": 0}
        )
        if not customer or not customer.get("phone"):
            await db.campaign_recipients.update_one(
                {"id": recipient["id"]},
                {"$set": {"status": RecipientStatus.OPTED_OUT.value, "error": "No phone number"}}
            )
            continue
        
        # Personalize message
        message = message_template
        message = message.replace("{first_name}", customer.get("first_name", ""))
        message = message.replace("{last_name}", customer.get("last_name", ""))
        message = message.replace("{company_name}", tenant.get("name", ""))
        
        try:
            # Send SMS
            result = await twilio_service.send_sms(
                to_phone=customer["phone"],
                body=message,
                from_phone=from_phone
            )
            
            # Update recipient status
            await db.campaign_recipients.update_one(
                {"id": recipient["id"]},
                {"$set": {
                    "status": RecipientStatus.SENT.value,
                    "last_message_at": datetime.now(timezone.utc).isoformat(),
                    "twilio_sid": result.get("provider_message_id")
                }}
            )
            sent_count += 1
            
            # Store message in conversation for tracking
            conv = await db.conversations.find_one(
                {"customer_id": customer["id"], "tenant_id": tenant_id},
                {"_id": 0}
            )
            if conv:
                msg = Message(
                    tenant_id=tenant_id,
                    conversation_id=conv["id"],
                    customer_id=customer["id"],
                    direction=MessageDirection.OUTBOUND,
                    sender_type=SenderType.SYSTEM,
                    channel=PreferredChannel.SMS,
                    content=message
                )
                msg_dict = msg.model_dump(mode='json')
                msg_dict["metadata"] = {"campaign_id": campaign_id, "twilio_sid": result.get("provider_message_id")}
                await db.messages.insert_one(msg_dict)
            
            # Also log to campaign_messages collection for campaign-specific tracking
            campaign_msg = {
                "id": str(uuid4()),
                "campaign_id": campaign_id,
                "tenant_id": tenant_id,
                "customer_id": customer["id"],
                "direction": "OUTBOUND",
                "content": message,
                "twilio_sid": result.get("provider_message_id"),
                "status": "SENT",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.campaign_messages.insert_one(campaign_msg)
            
        except Exception as e:
            errors.append({"customer_id": recipient["customer_id"], "error": str(e)})
            await db.campaign_recipients.update_one(
                {"id": recipient["id"]},
                {"$set": {"status": RecipientStatus.OPTED_OUT.value, "error": str(e)}}
            )
    
    # Get remaining count
    remaining = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.PENDING.value}
    )
    
    return {
        "status": "sending",
        "sent_in_batch": sent_count,
        "errors": len(errors),
        "remaining": remaining,
        "error_details": errors[:5] if errors else []
    }


@v1_router.get("/campaigns/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get real-time campaign statistics"""
    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Count recipients by status
    total = await db.campaign_recipients.count_documents({"campaign_id": campaign_id})
    pending = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.PENDING.value}
    )
    sent = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.SENT.value}
    )
    responded = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.RESPONDED.value}
    )
    opted_out = await db.campaign_recipients.count_documents(
        {"campaign_id": campaign_id, "status": RecipientStatus.OPTED_OUT.value}
    )
    
    # Calculate response rate
    response_rate = (responded / sent * 100) if sent > 0 else 0
    
    # Get recipients list
    recipients = await db.campaign_recipients.find(
        {"campaign_id": campaign_id},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with customer data
    enriched_recipients = []
    for r in recipients:
        customer = await db.customers.find_one({"id": r["customer_id"]}, {"_id": 0})
        if customer:
            enriched_recipients.append({
                **r,
                "customer_name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                "customer_phone": customer.get("phone", "")
            })
    
    return {
        "campaign_id": campaign_id,
        "campaign_status": campaign.get("status"),
        "stats": {
            "total": total,
            "pending": pending,
            "sent": sent,
            "responded": responded,
            "opted_out": opted_out,
            "response_rate": round(response_rate, 1)
        },
        "recipients": enriched_recipients
    }


@v1_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a campaign and its recipients"""
    result = await db.campaigns.delete_one({"id": campaign_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Delete associated recipients
    await db.campaign_recipients.delete_many({"campaign_id": campaign_id})
    
    # Delete associated campaign messages
    await db.campaign_messages.delete_many({"campaign_id": campaign_id})
    
    return {"status": "deleted", "campaign_id": campaign_id}


@v1_router.post("/campaigns/bulk-delete")
async def bulk_delete_campaigns(
    campaign_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete multiple campaigns at once"""
    deleted_count = 0
    for campaign_id in campaign_ids:
        result = await db.campaigns.delete_one({"id": campaign_id, "tenant_id": tenant_id})
        if result.deleted_count > 0:
            await db.campaign_recipients.delete_many({"campaign_id": campaign_id})
            await db.campaign_messages.delete_many({"campaign_id": campaign_id})
            deleted_count += 1
    
    return {"status": "deleted", "deleted_count": deleted_count}


@v1_router.get("/campaigns/customers-for-selection")
async def get_customers_for_campaign_selection(
    job_type: Optional[str] = None,
    last_service_days: Optional[int] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Get customers filtered by job type for campaign selection.
    job_type: DIAGNOSTIC, REPAIR, MAINTENANCE, INSTALLATION
    last_service_days: Filter by last service more than X days ago
    """
    import pytz
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")
    
    now = datetime.now(tenant_tz)
    
    # Build job filter
    job_filter = {"tenant_id": tenant_id, "status": "COMPLETED"}
    if job_type:
        job_filter["job_type"] = job_type.upper()
    
    # Get customers with matching jobs
    pipeline = [
        {"$match": job_filter},
        {"$sort": {"service_window_start": -1}},
        {"$group": {
            "_id": "$customer_id",
            "last_service": {"$first": "$service_window_start"},
            "job_types": {"$addToSet": "$job_type"},
            "job_count": {"$sum": 1}
        }}
    ]
    
    # Add date filter if specified
    if last_service_days:
        cutoff_date = now - timedelta(days=last_service_days)
        pipeline.append({"$match": {"last_service": {"$lt": cutoff_date.isoformat()}}})
    
    job_data = {}
    async for doc in db.jobs.aggregate(pipeline):
        if doc["_id"]:
            job_data[doc["_id"]] = {
                "last_service": doc["last_service"],
                "job_types": doc["job_types"],
                "job_count": doc["job_count"]
            }
    
    # Get customer details
    if job_data:
        customers = await db.customers.find(
            {"tenant_id": tenant_id, "id": {"$in": list(job_data.keys())}},
            {"_id": 0}
        ).to_list(500)
    else:
        # If no filter, get all customers
        customers = await db.customers.find(
            {"tenant_id": tenant_id},
            {"_id": 0}
        ).to_list(500)
    
    # Enrich with job data
    enriched_customers = []
    for c in customers:
        if c.get("phone"):  # Only include customers with phone
            customer_job_data = job_data.get(c["id"], {})
            enriched_customers.append({
                "id": c["id"],
                "first_name": c.get("first_name", ""),
                "last_name": c.get("last_name", ""),
                "phone": c.get("phone", ""),
                "email": c.get("email", ""),
                "last_service": customer_job_data.get("last_service"),
                "job_types": customer_job_data.get("job_types", []),
                "job_count": customer_job_data.get("job_count", 0)
            })
    
    # Get available job types for filter dropdown
    all_job_types = await db.jobs.distinct("job_type", {"tenant_id": tenant_id})
    
    return {
        "customers": enriched_customers,
        "total": len(enriched_customers),
        "available_job_types": all_job_types,
        "filters_applied": {
            "job_type": job_type,
            "last_service_days": last_service_days
        }
    }


@v1_router.post("/campaigns/{campaign_id}/start-with-customers")
async def start_campaign_with_selected_customers(
    campaign_id: str,
    customer_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Start a campaign with manually selected customers.
    """
    import pytz
    
    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] not in ["DRAFT", "PAUSED"]:
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign['status']}")
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")
    
    now = datetime.now(tenant_tz)
    
    # Get customer details
    customers = await db.customers.find(
        {"tenant_id": tenant_id, "id": {"$in": customer_ids}},
        {"_id": 0}
    ).to_list(len(customer_ids))
    
    # Filter customers with phone numbers
    customers_with_phone = [c for c in customers if c.get("phone")]
    
    # Delete existing recipients for this campaign (in case of restart)
    await db.campaign_recipients.delete_many({"campaign_id": campaign_id})
    
    # Create recipient records
    recipients_created = 0
    for customer in customers_with_phone:
        recipient = CampaignRecipient(
            campaign_id=campaign_id,
            customer_id=customer["id"],
            status=RecipientStatus.PENDING
        )
        recipient_dict = recipient.model_dump(mode='json')
        await db.campaign_recipients.insert_one(recipient_dict)
        recipients_created += 1
    
    # Update campaign status
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": CampaignStatus.RUNNING.value,
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "total_recipients": recipients_created,
            "selection_type": "manual",
            "selected_customer_ids": customer_ids
        }}
    )
    
    return {
        "status": "started",
        "campaign_id": campaign_id,
        "recipients_created": recipients_created,
        "message": f"Campaign started with {recipients_created} manually selected recipients."
    }


@v1_router.get("/campaigns/{campaign_id}/messages")
async def get_campaign_messages(
    campaign_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all SMS messages (outbound and inbound) for a specific campaign.
    """
    # Get campaign
    campaign = await db.campaigns.find_one(
        {"id": campaign_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get campaign messages from dedicated collection
    messages = await db.campaign_messages.find(
        {"campaign_id": campaign_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    # Enrich with customer data
    enriched_messages = []
    for msg in messages:
        customer = await db.customers.find_one(
            {"id": msg.get("customer_id")},
            {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1}
        )
        enriched_messages.append({
            **msg,
            "customer_name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() if customer else "Unknown",
            "customer_phone": customer.get("phone", "") if customer else ""
        })
    
    # Get stats
    outbound_count = len([m for m in messages if m.get("direction") == "OUTBOUND"])
    inbound_count = len([m for m in messages if m.get("direction") == "INBOUND"])
    
    return {
        "campaign_id": campaign_id,
        "messages": enriched_messages,
        "stats": {
            "total": len(messages),
            "outbound": outbound_count,
            "inbound": inbound_count
        }
    }


# ============= REPORTS ENDPOINT =============

@v1_router.get("/reports/summary")
async def get_reports_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get summary report for tenant"""
    # Default to last 30 days
    if not date_from:
        date_from = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = datetime.now(timezone.utc).isoformat()
    
    # Leads by source
    leads_pipeline = [
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": date_from, "$lte": date_to}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]
    leads_by_source = await db.leads.aggregate(leads_pipeline).to_list(100)
    
    # Jobs by status
    jobs_pipeline = [
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": date_from, "$lte": date_to}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    jobs_by_status = await db.jobs.aggregate(jobs_pipeline).to_list(100)
    
    # Quote stats
    total_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": date_from, "$lte": date_to}
    })
    accepted_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "status": QuoteStatus.ACCEPTED.value,
        "created_at": {"$gte": date_from, "$lte": date_to}
    })
    
    # Total counts
    total_leads = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": date_from, "$lte": date_to}
    })
    total_jobs = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": date_from, "$lte": date_to}
    })
    
    return {
        "period": {"from": date_from, "to": date_to},
        "leads": {
            "total": total_leads,
            "by_source": {item["_id"]: item["count"] for item in leads_by_source}
        },
        "jobs": {
            "total": total_jobs,
            "by_status": {item["_id"]: item["count"] for item in jobs_by_status}
        },
        "quotes": {
            "total": total_quotes,
            "accepted": accepted_quotes,
            "conversion_rate": round(accepted_quotes / total_quotes * 100, 1) if total_quotes > 0 else 0
        }
    }


# ============= SELF-HOSTED VOICE AI (TWILIO CONVERSATIONRELAY) =============

@v1_router.post("/voice/inbound")
async def voice_inbound(request: Request):
    """
    Handle inbound voice call from Twilio.
    Returns TwiML with ConversationRelay for real-time WebSocket streaming.
    
    ConversationRelay provides:
    - Real-time speech-to-text (STT) via Deepgram
    - Text-to-speech (TTS) via ElevenLabs (default) or others
    - Low-latency bidirectional WebSocket communication
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    from_phone = form_data.get("From", "").strip()
    to_phone = form_data.get("To", "").strip()
    
    if from_phone and not from_phone.startswith("+"):
        from_phone = "+" + from_phone.lstrip()
    if to_phone and not to_phone.startswith("+"):
        to_phone = "+" + to_phone.lstrip()
    
    logger.info(f"Inbound voice call: {call_sid} from {from_phone} to {to_phone}")
    
    # Find tenant by phone number
    tenant = await db.tenants.find_one({"twilio_phone_number": to_phone}, {"_id": 0})
    
    if not tenant:
        to_phone_digits = ''.join(c for c in to_phone if c.isdigit())
        tenant = await db.tenants.find_one({
            "$or": [
                {"twilio_phone_number": to_phone},
                {"twilio_phone_number": f"+{to_phone_digits}"},
                {"twilio_phone_number": to_phone_digits},
                {"twilio_phone_number": f"+1{to_phone_digits[-10:]}"} if len(to_phone_digits) >= 10 else {"twilio_phone_number": "NOMATCH"}
            ]
        }, {"_id": 0})
    
    if not tenant:
        logger.warning(f"No tenant found for phone number: {to_phone}")
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>We're sorry, this number is not configured.</Say>
    <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")
    
    # Get the backend URL and construct WebSocket URL
    base_url = os.environ.get('BACKEND_URL', os.environ.get('APP_BASE_URL', ''))
    
    # Convert https:// to wss:// for WebSocket connection
    if base_url.startswith('https://'):
        ws_url = base_url.replace('https://', 'wss://')
    elif base_url.startswith('http://'):
        ws_url = base_url.replace('http://', 'ws://')
    else:
        ws_url = f"wss://{base_url}"
    
    # Construct full WebSocket URL for ConversationRelay
    ws_endpoint = f"{ws_url}/api/v1/voice/ws/{call_sid}"
    
    # Check if OpenAI key is configured in Railway env (required for Voice AI)
    has_openai = os.environ.get("OPENAI_API_KEY")
    
    if not has_openai:
        # No AI configured - simple voicemail
        logger.warning("No OPENAI_API_KEY environment variable set")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling {tenant.get('name', 'us')}. Please leave a message after the beep.</Say>
    <Record maxLength="120" action="{base_url}/api/v1/voice/recording-complete" />
</Response>"""
        return Response(content=twiml, media_type="application/xml")
    
    # Check if tenant has voice system prompt configured
    if not tenant.get("voice_system_prompt"):
        logger.warning(f"No voice system prompt configured for tenant {tenant.get('id')}")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling {tenant.get('name', 'us')}. Please leave a message after the beep.</Say>
    <Record maxLength="120" action="{base_url}/api/v1/voice/recording-complete" />
</Response>"""
        return Response(content=twiml, media_type="application/xml")
    
    # Store call context for conversation
    await db.voice_calls.update_one(
        {"call_sid": call_sid},
        {"$set": {
            "call_sid": call_sid,
            "tenant_id": tenant["id"],
            "from_phone": from_phone,
            "to_phone": to_phone,
            "tenant_name": tenant.get("name", "our company"),
            "conversation_state": "greeting",
            "collected_info": {},
            "conversation_history": [],
            "started_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    # Get welcome greeting
    welcome = tenant.get('voice_greeting') or f"Hi, thanks for calling {tenant.get('name', 'us')}. How can I help you today?"
    
    # Escape XML special characters in welcome message
    welcome = welcome.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')
    
    # Get voice provider settings
    voice_provider = tenant.get('voice_provider', 'elevenlabs').lower()
    
    # Determine TTS provider and voice
    if voice_provider == 'elevenlabs':
        tts_provider = 'ElevenLabs'
        # Use tenant's ElevenLabs voice ID or default
        voice = tenant.get('elevenlabs_voice_id') or 'UgBBYS2sOqTuMpoF3BR0'  # Default ElevenLabs voice
    elif voice_provider == 'amazon':
        tts_provider = 'Amazon'
        voice = tenant.get('voice_name') or 'Joanna-Neural'
    else:
        tts_provider = 'Google'
        voice = tenant.get('voice_name') or 'en-US-Journey-O'
    
    # Build ConversationRelay TwiML
    # This is the proper format per Twilio documentation
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect action="{base_url}/api/v1/voice/connect-complete">
        <ConversationRelay 
            url="{ws_endpoint}"
            welcomeGreeting="{welcome}"
            welcomeGreetingInterruptible="any"
            language="en-US"
            ttsProvider="{tts_provider}"
            voice="{voice}"
            transcriptionProvider="Deepgram"
            speechModel="nova-3-general"
            interruptible="any"
            dtmfDetection="true"
        >
            <Parameter name="tenant_id" value="{tenant['id']}"/>
            <Parameter name="tenant_name" value="{tenant.get('name', 'Company')}"/>
            <Parameter name="caller_phone" value="{from_phone}"/>
        </ConversationRelay>
    </Connect>
</Response>"""
    
    logger.info(f"Voice AI (ConversationRelay) started for tenant {tenant['id']}, call {call_sid}")
    logger.info(f"WebSocket endpoint: {ws_endpoint}")
    return Response(content=twiml, media_type="application/xml")


@v1_router.post("/voice/connect-complete")
async def voice_connect_complete(request: Request):
    """
    Called by Twilio when the <Connect> verb completes (ConversationRelay session ends).
    This is the action URL for the Connect verb.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    session_id = form_data.get("SessionId", "")
    session_status = form_data.get("SessionStatus", "")
    session_duration = form_data.get("SessionDuration", "0")
    handoff_data = form_data.get("HandoffData", "")
    error_code = form_data.get("ErrorCode", "")
    error_message = form_data.get("ErrorMessage", "")
    
    logger.info(f"ConversationRelay session ended: {call_sid}")
    logger.info(f"  Session: {session_id}, Status: {session_status}, Duration: {session_duration}s")
    
    if error_code:
        logger.error(f"  Error: {error_code} - {error_message}")
    
    if handoff_data:
        logger.info(f"  Handoff data: {handoff_data}")
    
    # Update the voice call record with session end info
    await db.voice_calls.update_one(
        {"call_sid": call_sid},
        {"$set": {
            "session_id": session_id,
            "session_status": session_status,
            "session_duration_seconds": int(session_duration) if session_duration else 0,
            "handoff_data": handoff_data,
            "error_code": error_code if error_code else None,
            "error_message": error_message if error_message else None,
            "ended_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Return empty TwiML to end the call gracefully
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling. Goodbye!</Say>
    <Hangup/>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")


# Simple WebSocket test endpoint
@app.websocket("/ws/test")
async def ws_test(websocket: WebSocket):
    """Test WebSocket connectivity"""
    await websocket.accept()
    logger.info("Test WebSocket connected!")
    await websocket.send_text("WebSocket working!")
    await websocket.close()


@app.websocket("/api/v1/voice/ws/{call_sid}")
async def voice_ws(websocket: WebSocket, call_sid: str):
    """
    WebSocket endpoint for Twilio ConversationRelay.
    
    Handles real-time bidirectional communication:
    - Receives: setup, prompt (transcribed speech), interrupt, dtmf, error
    - Sends: text tokens for TTS synthesis
    """
    logger.info(f"ConversationRelay WebSocket connection attempt for call: {call_sid}")
    
    try:
        await websocket.accept()
        logger.info(f"ConversationRelay WebSocket CONNECTED: {call_sid}")
    except Exception as e:
        logger.error(f"WebSocket accept failed: {e}")
        return
    
    from services.conversation_relay import ConversationRelayHandler
    
    handler = None
    tenant = None
    caller_phone = ""
    
    try:
        # Get call context from database
        call_context = await db.voice_calls.find_one({"call_sid": call_sid}, {"_id": 0})
        
        if call_context:
            tenant = await db.tenants.find_one({"id": call_context.get("tenant_id")}, {"_id": 0})
            caller_phone = call_context.get("from_phone", "")
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event_type = message.get("type")
            
            logger.info(f"ConversationRelay event: {event_type}")
            logger.debug(f"Message payload: {json.dumps(message)[:500]}")
            
            if event_type == "setup":
                # Setup message contains session info and custom parameters
                session_id = message.get("sessionId", "")
                custom_params = message.get("customParameters", {})
                
                logger.info(f"ConversationRelay setup - SessionID: {session_id}")
                logger.info(f"Custom parameters: {custom_params}")
                
                # If we didn't have call context, try to get tenant from custom parameters
                if not tenant and custom_params.get("tenant_id"):
                    tenant = await db.tenants.find_one({"id": custom_params["tenant_id"]}, {"_id": 0})
                    caller_phone = custom_params.get("caller_phone", "")
                    logger.info(f"Got tenant from custom_params: {tenant.get('name') if tenant else 'None'}")
                
                if tenant:
                    logger.info(f"Creating handler for tenant: {tenant.get('name')}, has prompt: {bool(tenant.get('voice_system_prompt'))}")
                    handler = ConversationRelayHandler(
                        db=db,
                        call_sid=call_sid,
                        tenant=tenant,
                        caller_phone=caller_phone
                    )
                    await handler.handle_setup(message)
                    logger.info("Handler created successfully")
                else:
                    logger.error(f"No tenant found for call {call_sid}")
                    # Send end message to terminate
                    await websocket.send_text(json.dumps({
                        "type": "end",
                        "handoffData": json.dumps({"reason": "No tenant configured"})
                    }))
                    break
                    
            elif event_type == "prompt":
                # Prompt message contains transcribed speech from caller
                voice_prompt = message.get("voicePrompt", "")
                is_last = message.get("last", True)
                lang = message.get("lang", "en-US")
                
                logger.info(f"Caller said: '{voice_prompt}' (lang={lang}, last={is_last})")
                
                if handler and voice_prompt.strip():
                    try:
                        response = await handler.handle_prompt(message)
                        logger.info(f"Handler returned response: '{response}'")
                        
                        if response:
                            # Send text tokens for TTS synthesis
                            # ConversationRelay will convert this to speech
                            await websocket.send_text(json.dumps({
                                "type": "text",
                                "token": response,
                                "last": True
                            }))
                            logger.info(f"Sent response to Twilio: '{response}'")
                        else:
                            logger.warning("Handler returned empty response")
                    except Exception as e:
                        logger.error(f"Error in handle_prompt: {e}", exc_info=True)
                        # Send a fallback response
                        await websocket.send_text(json.dumps({
                            "type": "text",
                            "token": "I'm sorry, I'm having trouble. Could you repeat that?",
                            "last": True
                        }))
                else:
                    if not handler:
                        logger.error("No handler available for prompt event")
                    elif not voice_prompt.strip():
                        logger.warning("Empty voice prompt received")
                        
            elif event_type == "interrupt":
                # Caller interrupted the AI's speech
                utterance = message.get("utteranceUntilInterrupt", "")
                duration_ms = message.get("durationUntilInterruptMs", 0)
                logger.info(f"Caller interrupted after {duration_ms}ms. Partial: '{utterance}'")
                
                if handler:
                    await handler.handle_interrupt(message)
                    
            elif event_type == "dtmf":
                # Caller pressed a key
                digit = message.get("digit", "")
                logger.info(f"DTMF digit pressed: {digit}")
                
                if handler:
                    response = await handler.handle_dtmf(message)
                    if response:
                        await websocket.send_text(json.dumps({
                            "type": "text",
                            "token": response,
                            "last": True
                        }))
                        
            elif event_type == "error":
                # Error from ConversationRelay
                description = message.get("description", "Unknown error")
                logger.error(f"ConversationRelay error: {description}")
                
                if handler:
                    await handler.handle_error(message)
                    
            elif event_type == "end":
                # Session ending
                logger.info(f"ConversationRelay session ending for call {call_sid}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"ConversationRelay WebSocket disconnected: {call_sid}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
    except Exception as e:
        logger.error(f"ConversationRelay WebSocket error: {e}", exc_info=True)
    finally:
        if handler:
            await handler.handle_end()


@v1_router.get("/voice/audio/{audio_id}")
async def get_voice_audio(audio_id: str):
    """
    Serve ElevenLabs-generated audio for Twilio to play.
    This endpoint generates audio on-demand and streams it.
    """
    from starlette.responses import StreamingResponse
    from services.elevenlabs_service import elevenlabs_service
    
    # Get the text to speak from database
    audio_doc = await db.voice_audio.find_one({"audio_id": audio_id}, {"_id": 0})
    
    if not audio_doc or not audio_doc.get("text"):
        logger.error(f"No audio text found for ID: {audio_id}")
        # Return silent audio or error
        return Response(content=b"", media_type="audio/mpeg")
    
    text = audio_doc["text"]
    
    # Generate audio with ElevenLabs
    audio_data = elevenlabs_service.text_to_speech(
        text=text,
        voice="roger",  # Natural male voice
        stability=0.5,
        similarity_boost=0.75
    )
    
    if not audio_data:
        logger.error(f"Failed to generate audio for: {text}")
        # Fallback - return empty or use a backup
        return Response(content=b"", media_type="audio/mpeg")
    
    logger.info(f"Serving {len(audio_data)} bytes of ElevenLabs audio for: {text[:50]}...")
    
    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={audio_id}.mp3",
            "Cache-Control": "public, max-age=3600"
        }
    )


@v1_router.post("/voice/recording-complete")
async def voice_recording_complete(request: Request):
    """Handle completed voice recording (fallback when self-hosted not enabled)"""
    form_data = await request.form()
    recording_url = form_data.get("RecordingUrl", "")
    call_sid = form_data.get("CallSid", "")
    from_phone = form_data.get("From", "")
    to_phone = form_data.get("To", "")
    
    logger.info(f"Voice recording complete: {call_sid}, recording: {recording_url}")
    
    # Find tenant
    tenant = await db.tenants.find_one({
        "$or": [
            {"twilio_phone_number": to_phone},
            {"twilio_phone_number": to_phone.replace("+", "")},
        ]
    }, {"_id": 0})
    
    if tenant and recording_url:
        # Create a lead from the voicemail
        from_phone_normalized = normalize_phone_e164(from_phone)
        
        lead = {
            "id": str(uuid4()),
            "tenant_id": tenant["id"],
            "source": "MISSED_CALL_SMS",
            "channel": "VOICE",
            "status": "NEW",
            "caller_phone": from_phone_normalized,
            "description": f"Voicemail recording: {recording_url}",
            "urgency": "ROUTINE",
            "tags": ["voicemail"],
            "first_contact_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.leads.insert_one(lead)
        
        # Send SMS acknowledgment
        from services.twilio_service import twilio_service
        sms_msg = f"Hi! Thanks for calling {tenant.get('name')}. We received your voicemail and will call you back shortly."
        await twilio_service.send_sms(to_phone=from_phone_normalized, body=sms_msg)
    
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for your message. We will call you back shortly. Goodbye!</Say>
    <Hangup/>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@v1_router.post("/voice/process-speech")
async def voice_process_speech(request: Request):
    """
    Process speech input from caller and generate AI response.
    Uses the professional receptionist prompt for natural conversation.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    speech_result = form_data.get("SpeechResult", "")
    from_phone = form_data.get("From", "").strip()
    
    # Normalize phone
    if from_phone and not from_phone.startswith("+"):
        from_phone = "+" + from_phone.lstrip()
    
    logger.info(f"Voice AI processing: '{speech_result}' from {from_phone}")
    
    base_url = os.environ.get('BACKEND_URL', os.environ.get('APP_BASE_URL', ''))
    
    # Get call context
    call_context = await db.voice_calls.find_one({"call_sid": call_sid}, {"_id": 0})
    
    if not call_context:
        logger.error(f"No call context for {call_sid}")
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew-Neural">I'm sorry, there was an error. Please call back.</Say>
    <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")
    
    tenant_id = call_context.get("tenant_id")
    tenant_name = call_context.get("tenant_name", "our company")
    conversation_state = call_context.get("conversation_state", "greeting")
    collected_info = call_context.get("collected_info", {})
    
    # Get from_phone from context if not in form
    if not from_phone:
        from_phone = call_context.get("from_phone", "")
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    
    # Find existing customer
    customer = None
    if from_phone:
        customer = await db.customers.find_one(
            {"phone": from_phone, "tenant_id": tenant_id},
            {"_id": 0}
        )
    
    try:
        from openai import AsyncOpenAI
        from services.voice_ai_prompt import get_voice_ai_prompt
        
        # Use tenant's OpenAI key (multi-tenant)
        openai_key = tenant.get("openai_api_key") if tenant else None
        if not openai_key:
            logger.error("No OpenAI API key configured for tenant")
            return Response(content="Error: API not configured", media_type="text/plain")
        
        client = AsyncOpenAI(api_key=openai_key)
        
        # Get conversation history from call context
        conversation_history = call_context.get("conversation_history", [])
        conversation_history.append({"role": "user", "content": speech_result})
        
        system_prompt = get_voice_ai_prompt(
            company_name=tenant_name,
            caller_phone=from_phone,
            collected_info=collected_info,
            conversation_state=conversation_state
        )
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": "Respond to the caller. Follow the order: Name → Phone → Address → Issue → Urgency → Book"})
        
        response_obj = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        response = response_obj.choices[0].message.content
        
        # Parse AI response
        try:
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            ai_response = json.loads(response_text)
        except json.JSONDecodeError:
            ai_response = {
                "response_text": response[:150] if len(response) < 150 else "Got it. What else can you tell me?",
                "next_state": conversation_state,
                "collected_data": {},
                "action": None
            }
        
        # Update collected info
        if ai_response.get("collected_data"):
            collected_info.update({k: v for k, v in ai_response["collected_data"].items() if v})
        
        next_state = ai_response.get("next_state", conversation_state)
        action = ai_response.get("action")
        response_text = ai_response.get("response_text", "Got it.")
        
        # Auto-detect if we should book when all info is collected
        has_name = bool(collected_info.get("name"))
        has_phone = collected_info.get("phone_confirmed", False) or bool(collected_info.get("phone"))
        has_address = collected_info.get("address_confirmed", False) or bool(collected_info.get("address"))
        has_issue = bool(collected_info.get("issue"))
        has_urgency = bool(collected_info.get("urgency"))
        
        # If all info collected and user confirmed/agreed, trigger booking
        all_info_collected = has_name and has_phone and has_address and has_issue and has_urgency
        user_confirmed = any(word in speech_result.lower() for word in ["yes", "yeah", "works", "good", "okay", "ok", "sure", "fine", "correct", "right"])
        
        if all_info_collected and user_confirmed and action != "book_job":
            logger.info(f"Auto-triggering booking - all info collected and user confirmed")
            action = "book_job"
            next_state = "booking_complete"
        
        # Ensure we have phone from caller ID if not provided differently
        if not collected_info.get("phone"):
            collected_info["phone"] = from_phone
        
        # Save AI response to history
        conversation_history.append({"role": "assistant", "content": response_text})
        
        # Update call context with history
        await db.voice_calls.update_one(
            {"call_sid": call_sid},
            {"$set": {
                "conversation_state": next_state,
                "collected_info": collected_info,
                "conversation_history": conversation_history,
                "last_speech": speech_result,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Handle booking action
        if action == "book_job" or next_state == "booking_complete":
            confirmed_phone = collected_info.get("phone") or from_phone
            
            result = await _voice_ai_book_job(
                tenant_id=tenant_id,
                from_phone=confirmed_phone,
                collected_info=collected_info,
                customer=customer
            )
            
            if result.get("success"):
                job = result.get("job", {})
                quote_amount = job.get("quote_amount", 89)
                customer_name = collected_info.get('name', '').split()[0] if collected_info.get('name') else ''
                address = collected_info.get('address', 'your location')
                
                # Send SMS
                from services.twilio_service import twilio_service
                sms_body = f"Hi {customer_name}! Your appointment with {tenant_name} is confirmed for tomorrow morning at {address}. Quote: ${quote_amount:.2f}. We'll text when the tech is on the way."
                await twilio_service.send_sms(to_phone=confirmed_phone, body=sms_body)
                
                # Final confirmation message
                final_text = f"Perfect, you're all set for tomorrow morning at {address}. You'll get a text confirmation shortly. Thanks for calling {tenant_name}!"
                audio_id = f"final_{call_sid}"
                await db.voice_audio.update_one(
                    {"audio_id": audio_id},
                    {"$set": {"text": final_text}},
                    upsert=True
                )
                
                twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{base_url}/api/v1/voice/audio/{audio_id}</Play>
    <Hangup/>
</Response>"""
            else:
                twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew-Neural">I apologize, I couldn't complete your booking. Someone will call you back shortly.</Say>
    <Hangup/>
</Response>"""
            
            return Response(content=twiml, media_type="application/xml")
        
        elif next_state == "end_call":
            await _voice_ai_create_lead(
                tenant_id=tenant_id,
                from_phone=collected_info.get("phone") or from_phone,
                collected_info=collected_info,
                customer=customer,
                speech_transcript=speech_result
            )
            
            goodbye_text = f"{response_text} Thanks for calling {tenant_name}!"
            audio_id = f"goodbye_{call_sid}"
            await db.voice_audio.update_one(
                {"audio_id": audio_id},
                {"$set": {"text": goodbye_text}},
                upsert=True
            )
            
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{base_url}/api/v1/voice/audio/{audio_id}</Play>
    <Hangup/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")
        
        else:
            # Continue conversation
            audio_id = f"resp_{call_sid}_{hash(response_text) % 10000}"
            await db.voice_audio.update_one(
                {"audio_id": audio_id},
                {"$set": {"text": response_text}},
                upsert=True
            )
            
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="{base_url}/api/v1/voice/process-speech" method="POST" speechTimeout="auto" language="en-US" enhanced="true">
        <Play>{base_url}/api/v1/voice/audio/{audio_id}</Play>
    </Gather>
    <Say voice="Polly.Matthew-Neural">I didn't catch that.</Say>
    <Gather input="speech" action="{base_url}/api/v1/voice/process-speech" method="POST" speechTimeout="auto" language="en-US" enhanced="true">
        <Say voice="Polly.Matthew-Neural">Are you still there?</Say>
    </Gather>
    <Say voice="Polly.Matthew-Neural">I'll have someone call you back. Goodbye.</Say>
    <Hangup/>
</Response>"""
            return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Voice AI error: {e}")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Matthew-Neural">I apologize for the technical difficulty. Let me transfer you.</Say>
    <Record maxLength="120" action="{base_url}/api/v1/voice/recording-complete" />
</Response>"""
        return Response(content=twiml, media_type="application/xml")


async def _voice_ai_book_job(tenant_id: str, from_phone: str, collected_info: dict, customer: dict = None):
    """Helper function to create lead, customer, property, and job from voice AI"""
    try:
        import pytz
        
        tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
        if not tenant:
            logger.error(f"Tenant not found: {tenant_id}")
            return {"success": False, "error": "Tenant not found"}
        
        tenant_tz = pytz.timezone(tenant.get("timezone", "America/New_York"))
        
        # Create or get customer
        customer_id = None
        if customer:
            customer_id = customer["id"]
        else:
            # Create new customer
            name_parts = collected_info.get("name", "").split() if collected_info.get("name") else [""]
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            
            new_customer = {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "first_name": first_name,
                "last_name": last_name,
                "phone": from_phone,
                "preferred_channel": "CALL",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.customers.insert_one(new_customer)
            customer_id = new_customer["id"]
            customer = new_customer
        
        # Create lead
        urgency = collected_info.get("urgency", "ROUTINE").upper()
        if urgency not in ["EMERGENCY", "URGENT", "ROUTINE"]:
            urgency = "ROUTINE"
        
        lead = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "source": "SELF_HOSTED_VOICE",
            "channel": "VOICE",
            "status": "JOB_BOOKED",
            "caller_name": collected_info.get("name", ""),
            "caller_phone": from_phone,
            "issue_type": collected_info.get("issue", "General Inquiry")[:100],
            "description": collected_info.get("issue", ""),
            "urgency": urgency,
            "tags": ["voice_ai", "self_hosted"],
            "first_contact_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.leads.insert_one(lead)
        
        # Determine job schedule (tomorrow morning by default)
        tomorrow = datetime.now(tenant_tz) + timedelta(days=1)
        if urgency == "EMERGENCY":
            # Same day if possible
            now = datetime.now(tenant_tz)
            if now.hour < 16:  # Before 4 PM, schedule for today afternoon
                service_date = now
                start_hour, end_hour = 14, 18
            else:
                service_date = tomorrow
                start_hour, end_hour = 8, 12
        else:
            service_date = tomorrow
            start_hour, end_hour = 8, 12
        
        service_window_start = tenant_tz.localize(
            datetime(service_date.year, service_date.month, service_date.day, start_hour, 0)
        )
        service_window_end = tenant_tz.localize(
            datetime(service_date.year, service_date.month, service_date.day, end_hour, 0)
        )
        
        # Calculate quote
        job_type = "DIAGNOSTIC"
        quote_amount = calculate_quote_amount(job_type, urgency)
        
        # Get or create property with the collected address
        property_id = None
        existing_prop = await db.properties.find_one({"customer_id": customer_id}, {"_id": 0})
        
        if existing_prop:
            property_id = existing_prop["id"]
            # Update address if we have a new one
            if collected_info.get("address"):
                await db.properties.update_one(
                    {"id": property_id},
                    {"$set": {"address_line1": collected_info["address"], "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
        elif collected_info.get("address"):
            # Create new property with the address
            new_property = {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "address_line1": collected_info["address"],
                "property_type": "RESIDENTIAL",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.properties.insert_one(new_property)
            property_id = new_property["id"]
            logger.info(f"Created property {property_id} with address: {collected_info['address']}")
        
        # Create job
        job = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "property_id": property_id,
            "lead_id": lead["id"],
            "job_type": job_type,
            "priority": "EMERGENCY" if urgency == "EMERGENCY" else ("HIGH" if urgency == "URGENT" else "NORMAL"),
            "service_window_start": service_window_start.isoformat(),
            "service_window_end": service_window_end.isoformat(),
            "status": "BOOKED",
            "created_by": "AI",
            "notes": collected_info.get("issue", ""),
            "quote_amount": quote_amount,
            "reminder_day_before_sent": False,
            "reminder_morning_of_sent": False,
            "en_route_sms_sent": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.jobs.insert_one(job)
        
        # Create quote
        quote = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "property_id": property_id,
            "job_id": job["id"],
            "amount": quote_amount,
            "currency": "USD",
            "description": f"{job_type} service - {collected_info.get('issue', 'General service')[:100]}",
            "status": "SENT",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.quotes.insert_one(quote)
        
        # Update job with quote_id
        await db.jobs.update_one({"id": job["id"]}, {"$set": {"quote_id": quote["id"]}})
        
        logger.info(f"Voice AI booked job {job['id']} for customer {customer_id}")
        
        return {
            "success": True,
            "job": job,
            "quote": quote,
            "lead": lead,
            "customer_id": customer_id
        }
        
    except Exception as e:
        logger.error(f"Voice AI booking error: {e}")
        return {"success": False, "error": str(e)}


async def _voice_ai_create_lead(tenant_id: str, from_phone: str, collected_info: dict, customer: dict = None, speech_transcript: str = ""):
    """Helper function to create just a lead from voice AI (without booking)"""
    try:
        customer_id = customer["id"] if customer else None
        
        urgency = collected_info.get("urgency", "ROUTINE").upper()
        if urgency not in ["EMERGENCY", "URGENT", "ROUTINE"]:
            urgency = "ROUTINE"
        
        lead = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "source": "SELF_HOSTED_VOICE",
            "channel": "VOICE",
            "status": "NEW",
            "caller_name": collected_info.get("name", ""),
            "caller_phone": from_phone,
            "issue_type": collected_info.get("issue", "General Inquiry")[:100] if collected_info.get("issue") else "Voice Inquiry",
            "description": f"Voice AI transcript: {speech_transcript}\n\nCollected info: {json.dumps(collected_info)}",
            "urgency": urgency,
            "tags": ["voice_ai", "self_hosted", "needs_followup"],
            "first_contact_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.leads.insert_one(lead)
        
        logger.info(f"Voice AI created lead {lead['id']}")
        return {"success": True, "lead": lead}
        
    except Exception as e:
        logger.error(f"Voice AI lead creation error: {e}")
        return {"success": False, "error": str(e)}


@v1_router.post("/voice/status")
async def voice_call_status(request: Request):
    """Handle Twilio call status callbacks"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    
    logger.info(f"Voice call status: {call_sid} -> {call_status}")
    
    # Could update lead/job status based on call outcome
    return {"received": True}


# WebSocket endpoint for real-time audio streaming
# Note: This would need to be run separately or with a proper WebSocket server
# For production, consider using a separate service or Twilio's Programmable Voice
@app.websocket("/api/v1/voice/stream/{call_sid}")
async def voice_stream_websocket(websocket: WebSocket, call_sid: str):
    """
    WebSocket endpoint for Twilio Media Streams.
    Handles real-time audio streaming for voice AI.
    """
    await websocket.accept()
    
    from services.voice_ai_service import create_voice_ai_service
    voice_ai = create_voice_ai_service()
    
    tenant_id = None
    from_phone = None
    stream_sid = None
    greeting_sent = False
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            event_type = message.get("event")
            
            if event_type == "connected":
                logger.info(f"WebSocket connected for call {call_sid}")
                
            elif event_type == "start":
                # Extract parameters from stream start
                start_data = message.get("start", {})
                stream_sid = start_data.get("streamSid")
                custom_params = start_data.get("customParameters", {})
                
                tenant_id = custom_params.get("tenant_id")
                from_phone = custom_params.get("from_phone")
                
                logger.info(f"Stream started: {stream_sid}, tenant: {tenant_id}")
                
                # Initialize voice AI
                if tenant_id:
                    await voice_ai.initialize(tenant_id, from_phone, call_sid, db)
                    
                    # Send greeting
                    if not greeting_sent:
                        greeting_audio = await voice_ai.get_greeting()
                        if greeting_audio:
                            await websocket.send_json({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": greeting_audio}
                            })
                            greeting_sent = True
                
            elif event_type == "media":
                # Receive audio chunk from caller
                media_data = message.get("media", {})
                audio_payload = media_data.get("payload", "")
                
                if audio_payload:
                    import base64
                    audio_chunk = base64.b64decode(audio_payload)
                    
                    # Process audio through STT
                    transcript = await voice_ai.process_audio(audio_chunk)
                    
                    if transcript:
                        logger.info(f"Transcript: {transcript}")
                        
                        # Generate AI response
                        response_audio, action_data = await voice_ai.generate_response(transcript)
                        
                        if response_audio:
                            await websocket.send_json({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": response_audio}
                            })
                        
                        # Handle actions
                        if action_data and action_data.get("action") == "end_call":
                            await websocket.send_json({
                                "event": "stop",
                                "streamSid": stream_sid
                            })
                            break
                
            elif event_type == "stop":
                logger.info(f"Stream stopped: {stream_sid}")
                await voice_ai.end_conversation()
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call {call_sid}")
        await voice_ai.end_conversation()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await voice_ai.end_conversation()


# ============= WEB FORM API (PUBLIC) =============

@v1_router.post("/webform/submit")
async def submit_web_form(data: WebFormLeadRequest):
    """
    Public endpoint for web form lead submission.
    Creates lead, customer, and optionally sends SMS confirmation.
    
    No authentication required - use tenant_slug to identify the business.
    
    Example request:
    POST /api/v1/webform/submit
    {
        "tenant_slug": "radiance-hvac",
        "name": "John Smith",
        "phone": "+12155551234",
        "email": "john@example.com",
        "address": "123 Main St",
        "city": "Philadelphia",
        "state": "PA",
        "zip_code": "19001",
        "issue_description": "AC not cooling properly",
        "urgency": "URGENT",
        "send_confirmation_sms": true
    }
    """
    from services.twilio_service import twilio_service
    import pytz
    
    # Get tenant by slug
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Business not found")
    
    tenant_id = tenant["id"]
    tenant_tz_str = tenant.get("timezone", "America/New_York")
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")
    
    now = datetime.now(tenant_tz)
    
    # Normalize phone number to E.164 format
    phone = normalize_phone_e164(data.phone)
    
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    
    # Parse name
    name_parts = data.name.strip().split(' ', 1) if data.name else ["Unknown"]
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    # Find or create customer
    customer = await db.customers.find_one({"phone": phone, "tenant_id": tenant_id}, {"_id": 0})
    
    if not customer:
        customer_id = str(uuid4())
        customer = {
            "id": customer_id,
            "tenant_id": tenant_id,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "email": data.email if data.email else None,
            "preferred_channel": "SMS",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.customers.insert_one(customer)
        logger.info(f"Created customer from web form: {customer_id}")
    else:
        customer_id = customer["id"]
        # Update email if provided and not set
        if data.email and not customer.get("email"):
            await db.customers.update_one(
                {"id": customer_id},
                {"$set": {"email": data.email, "updated_at": now.isoformat()}}
            )
    
    # Create property if address provided
    property_id = None
    if data.address:
        property_id = str(uuid4())
        prop = {
            "id": property_id,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "address_line1": data.address,
            "city": data.city or "",
            "state": data.state or "",
            "postal_code": data.zip_code or "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.properties.insert_one(prop)
    
    # Create lead
    lead_id = str(uuid4())
    urgency_value = data.urgency.upper() if data.urgency else "ROUTINE"
    if urgency_value not in ["EMERGENCY", "URGENT", "ROUTINE"]:
        urgency_value = "ROUTINE"
    
    lead = Lead(
        tenant_id=tenant_id,
        customer_id=customer_id,
        property_id=property_id,
        source=LeadSource.WEB_FORM,
        channel=LeadChannel.FORM,
        status=LeadStatus.NEW,
        urgency=Urgency(urgency_value),
        description=data.issue_description,
        caller_name=data.name,
        caller_phone=phone
    )
    lead_dict = lead.model_dump(mode='json')
    lead_dict["id"] = lead_id
    
    # Add preferred scheduling if provided
    if data.preferred_date:
        lead_dict["preferred_date"] = data.preferred_date
    if data.preferred_time:
        lead_dict["preferred_time"] = data.preferred_time
    
    await db.leads.insert_one(lead_dict)
    logger.info(f"Created lead from web form: {lead_id}")
    
    # Create or get conversation
    conv = await db.conversations.find_one(
        {"customer_id": customer_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    
    if not conv:
        conv_id = str(uuid4())
        conv = {
            "id": conv_id,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "status": "OPEN",
            "primary_channel": "SMS",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.conversations.insert_one(conv)
    else:
        conv_id = conv["id"]
    
    # Send AI-powered initial SMS to start booking conversation
    sms_sent = False
    sms_error = None
    
    if data.send_confirmation_sms and tenant.get("twilio_phone_number"):
        try:
            from services.ai_sms_service import ai_sms_service
            
            company_name = tenant.get("name", "Our company")
            
            # Generate AI-powered initial message
            initial_msg = await ai_sms_service.generate_initial_message(
                customer_name=first_name,
                issue_description=data.issue_description or "service request",
                company_name=company_name
            )
            
            result = await twilio_service.send_sms(
                to_phone=phone,
                body=initial_msg,
                from_phone=tenant["twilio_phone_number"]
            )
            sms_sent = True
            
            # Store outbound message and mark conversation for AI handling
            msg = Message(
                tenant_id=tenant_id,
                conversation_id=conv_id,
                customer_id=customer_id,
                direction=MessageDirection.OUTBOUND,
                sender_type=SenderType.AI,  # Mark as AI message
                channel=PreferredChannel.SMS,
                content=initial_msg
            )
            msg_dict = msg.model_dump(mode='json')
            msg_dict["metadata"] = {
                "source": "web_form_ai_booking",
                "lead_id": lead_id,
                "ai_booking_active": True
            }
            await db.messages.insert_one(msg_dict)
            
            # Update conversation to track AI booking state
            await db.conversations.update_one(
                {"id": conv_id},
                {"$set": {
                    "ai_booking_active": True,
                    "ai_booking_lead_id": lead_id,
                    "ai_booking_context": {
                        "customer_name": f"{first_name} {last_name}".strip(),
                        "issue_description": data.issue_description,
                        "urgency": urgency_value,
                        "address": f"{data.address or ''}, {data.city or ''}, {data.state or ''} {data.zip_code or ''}".strip(", "),
                        "property_id": property_id
                    },
                    "updated_at": now.isoformat()
                }}
            )
            
            logger.info(f"Started AI booking conversation for web form lead {lead_id}")
            
        except Exception as e:
            logger.error(f"Failed to start AI SMS conversation: {str(e)}")
            sms_error = str(e)
    
    return {
        "success": True,
        "lead_id": lead_id,
        "customer_id": customer_id,
        "property_id": property_id,
        "conversation_id": conv_id,
        "sms_sent": sms_sent,
        "sms_error": sms_error,
        "message": f"Thank you, {first_name}! Your request has been received. {'We sent a confirmation to your phone.' if sms_sent else 'We will contact you shortly.'}"
    }


# ============= INBOUND SMS WEBHOOK =============

def normalize_phone(phone: str) -> str:
    """Normalize phone number to +1XXXXXXXXXX format"""
    if not phone:
        return ""
    # Remove all non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())
    # Add country code if missing
    if len(digits) == 10:
        digits = '1' + digits
    # Add + prefix
    return '+' + digits if digits else ""

@v1_router.post("/sms/inbound")
async def sms_inbound(request: Request):
    """Handle inbound SMS from Twilio webhook"""
    form_data = await request.form()
    
    from_phone_raw = form_data.get("From", "")
    to_phone_raw = form_data.get("To", "")
    body = form_data.get("Body", "")
    
    # Normalize phone numbers
    from_phone = normalize_phone(from_phone_raw)
    to_phone = normalize_phone(to_phone_raw)
    
    logger.info(f"Inbound SMS from {from_phone} to {to_phone}: {body[:50]}...")
    
    # Find tenant by Twilio phone number (try both normalized and raw)
    tenant = await db.tenants.find_one({"twilio_phone_number": to_phone}, {"_id": 0})
    if not tenant:
        tenant = await db.tenants.find_one({"twilio_phone_number": to_phone_raw}, {"_id": 0})
    if not tenant:
        # Fallback to first tenant for this deployment
        tenant = await db.tenants.find_one({}, {"_id": 0})
        if not tenant:
            logger.error(f"No tenant found for number {to_phone}")
            return {"status": "no_tenant"}
    
    tenant_id = tenant["id"]
    
    # Find customer by phone (try multiple formats)
    customer = await db.customers.find_one(
        {"phone": from_phone, "tenant_id": tenant_id}, {"_id": 0}
    )
    if not customer:
        # Try with raw phone
        customer = await db.customers.find_one(
            {"phone": from_phone_raw, "tenant_id": tenant_id}, {"_id": 0}
        )
    if not customer:
        # Try regex match on last 10 digits
        phone_digits = ''.join(c for c in from_phone if c.isdigit())[-10:]
        if phone_digits:
            customer = await db.customers.find_one(
                {"phone": {"$regex": phone_digits}, "tenant_id": tenant_id}, {"_id": 0}
            )
    
    if not customer:
        # Create new customer with normalized phone
        customer = Customer(
            tenant_id=tenant_id,
            first_name="Unknown",
            last_name="",
            phone=from_phone
        )
        customer_dict = customer.model_dump(mode='json')
        await db.customers.insert_one(customer_dict)
        customer = customer_dict
        logger.info(f"Created new customer for phone {from_phone}")
    
    # Find or create conversation
    conv = await db.conversations.find_one(
        {"customer_id": customer["id"], "tenant_id": tenant_id, "status": ConversationStatus.OPEN.value},
        {"_id": 0}
    )
    
    if not conv:
        conv = Conversation(
            tenant_id=tenant_id,
            customer_id=customer["id"],
            primary_channel=PreferredChannel.SMS,
            status=ConversationStatus.OPEN
        )
        conv_dict = conv.model_dump(mode='json')
        await db.conversations.insert_one(conv_dict)
        conv = conv_dict
    
    # Create inbound message
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=conv["id"],
        customer_id=customer["id"],
        direction=MessageDirection.INBOUND,
        sender_type=SenderType.CUSTOMER,
        channel=PreferredChannel.SMS,
        content=body
    )
    msg_dict = msg.model_dump(mode='json')
    await db.messages.insert_one(msg_dict)
    
    # Check if this customer has any active campaign - log as campaign response
    active_recipient = await db.campaign_recipients.find_one({
        "customer_id": customer["id"],
        "status": {"$in": [RecipientStatus.SENT.value, RecipientStatus.PENDING.value]}
    }, {"_id": 0})
    
    if active_recipient:
        campaign_id = active_recipient.get("campaign_id")
        
        # Update recipient status to RESPONDED
        await db.campaign_recipients.update_one(
            {"id": active_recipient["id"]},
            {"$set": {
                "status": RecipientStatus.RESPONDED.value,
                "response": body,
                "responded_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Log inbound message to campaign_messages
        campaign_msg = {
            "id": str(uuid4()),
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
            "customer_id": customer["id"],
            "direction": "INBOUND",
            "content": body,
            "status": "RECEIVED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.campaign_messages.insert_one(campaign_msg)
        logger.info(f"Campaign response logged from {from_phone} for campaign {campaign_id}")
    
    # Update conversation
    await db.conversations.update_one(
        {"id": conv["id"]},
        {"$set": {
            "last_message_from": SenderType.CUSTOMER.value,
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Check if this is an AI booking conversation (from webform)
    if conv.get("ai_booking_active"):
        try:
            from services.ai_sms_service import ai_sms_service
            import pytz
            
            # Get conversation history
            history = await db.messages.find(
                {"conversation_id": conv["id"]}, {"_id": 0}
            ).sort("created_at", -1).limit(10).to_list(10)
            history.reverse()
            
            # Build context for AI
            booking_context = conv.get("ai_booking_context", {})
            booking_context["conversation_id"] = conv["id"]
            booking_context["message_history"] = history
            
            # Process with AI booking service
            ai_result = await ai_sms_service.process_sms_reply(
                customer_message=body,
                conversation_context=booking_context,
                tenant_info=tenant
            )
            
            logger.info(f"AI booking result: {ai_result}")
            
            # Send AI response
            if tenant.get("twilio_phone_number") and ai_result and ai_result.get("response_text"):
                from services.twilio_service import twilio_service
                
                sms_result = await twilio_service.send_sms(
                    to_phone=from_phone,
                    body=ai_result["response_text"],
                    from_phone=tenant["twilio_phone_number"]
                )
                
                # Log AI response
                ai_msg = Message(
                    tenant_id=tenant_id,
                    conversation_id=conv["id"],
                    customer_id=customer["id"],
                    direction=MessageDirection.OUTBOUND,
                    sender_type=SenderType.AI,
                    channel=PreferredChannel.SMS,
                    content=ai_result["response_text"],
                    metadata={"twilio_sid": sms_result.get("provider_message_id"), "ai_booking": True}
                )
                ai_msg_dict = ai_msg.model_dump(mode='json')
                await db.messages.insert_one(ai_msg_dict)
                
                # If AI determined we should book a job
                if ai_result.get("action") == "book_job" and ai_result.get("booking_data"):
                    try:
                        booking_data = ai_result["booking_data"]
                        
                        # Validate booking data has required fields
                        if not booking_data.get("date") or not booking_data.get("time_slot"):
                            logger.warning(f"Incomplete booking data: {booking_data}")
                        else:
                            # Parse the booking date and time slot
                            tenant_tz = pytz.timezone(tenant.get("timezone", "America/New_York"))
                            booking_date = datetime.strptime(booking_data["date"], "%Y-%m-%d")
                            
                            time_slots = {
                                "morning": (8, 12),
                                "afternoon": (12, 16),
                                "evening": (16, 19)
                            }
                            slot = time_slots.get(booking_data.get("time_slot", "morning"), (8, 12))
                            
                            window_start = tenant_tz.localize(datetime(
                                booking_date.year, booking_date.month, booking_date.day,
                                slot[0], 0, 0
                            ))
                            window_end = tenant_tz.localize(datetime(
                                booking_date.year, booking_date.month, booking_date.day,
                                slot[1], 0, 0
                            ))
                            
                            # Get property from context
                            property_id = booking_context.get("property_id")
                            lead_id = conv.get("ai_booking_lead_id")
                            
                            # Determine job type and calculate quote
                            job_type_str = booking_data.get("job_type", "DIAGNOSTIC").upper()
                            if job_type_str not in ["DIAGNOSTIC", "REPAIR", "MAINTENANCE", "INSTALL"]:
                                job_type_str = "DIAGNOSTIC"
                            
                            urgency = booking_context.get("urgency", "ROUTINE")
                            quote_amount = calculate_quote_amount(job_type_str, urgency)
                            
                            # Create the job
                            job = Job(
                                tenant_id=tenant_id,
                                customer_id=customer["id"],
                                property_id=property_id,
                                lead_id=lead_id,
                                job_type=JobType(job_type_str),
                                priority=JobPriority.NORMAL,
                                service_window_start=window_start,
                                service_window_end=window_end,
                                status=JobStatus.BOOKED,
                                created_by=JobCreatedBy.AI,
                                quote_amount=quote_amount
                            )
                            
                            job_dict = job.model_dump(mode='json')
                            await db.jobs.insert_one(job_dict)
                            
                            # Create quote
                            quote = Quote(
                                tenant_id=tenant_id,
                                customer_id=customer["id"],
                                property_id=property_id,
                                job_id=job.id,
                                amount=quote_amount,
                                description=f"{job_type_str} - {booking_context.get('issue_description', 'Service')}",
                                status=QuoteStatus.SENT
                            )
                            quote_dict = quote.model_dump(mode='json')
                            quote_dict["sent_at"] = datetime.now(timezone.utc).isoformat()
                            await db.quotes.insert_one(quote_dict)
                            
                            # Link quote to job
                            await db.jobs.update_one({"id": job.id}, {"$set": {"quote_id": quote.id}})
                            
                            # Update lead status
                            if lead_id:
                                await db.leads.update_one(
                                    {"id": lead_id},
                                    {"$set": {"status": LeadStatus.JOB_BOOKED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
                                )
                            
                            # Send quote SMS (continuation)
                            quote_msg = f"Your service quote for {job_type_str} is ${quote_amount:.2f}. Pay securely here: [YOUR PAYMENT LINK HERE]. Reply with any questions!"
                            
                            await twilio_service.send_sms(
                                to_phone=from_phone,
                                body=quote_msg,
                                from_phone=tenant["twilio_phone_number"]
                            )
                            
                            # Log quote SMS
                            quote_sms_msg = Message(
                                tenant_id=tenant_id,
                                conversation_id=conv["id"],
                                customer_id=customer["id"],
                                direction=MessageDirection.OUTBOUND,
                                sender_type=SenderType.SYSTEM,
                                channel=PreferredChannel.SMS,
                                content=quote_msg,
                                metadata={"quote_id": quote.id, "job_id": job.id}
                            )
                            quote_sms_dict = quote_sms_msg.model_dump(mode='json')
                            await db.messages.insert_one(quote_sms_dict)
                            
                            # Mark AI booking as complete
                            await db.conversations.update_one(
                                {"id": conv["id"]},
                                {"$set": {
                                    "ai_booking_active": False,
                                    "ai_booking_completed": True,
                                    "ai_booking_job_id": job.id,
                                    "updated_at": datetime.now(timezone.utc).isoformat()
                                }}
                            )
                            
                            logger.info(f"AI booking completed: Job {job.id} created for customer {customer['id']}")
                    except Exception as booking_err:
                        logger.error(f"Error processing booking data: {booking_err}")
                
                # Update conversation timestamp
                await db.conversations.update_one(
                    {"id": conv["id"]},
                    {"$set": {
                        "last_message_from": SenderType.AI.value,
                        "last_message_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            
            return {"status": "received", "ai_booking": True}
            
        except Exception as e:
            import traceback
            logger.error(f"Error in AI booking conversation: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fall through to regular AI handling
    
    # Regular AI response (non-booking conversations)
    try:
        from services.openai_service import openai_service
        
        # Get conversation history
        history = await db.messages.find(
            {"conversation_id": conv["id"]}, {"_id": 0}
        ).sort("created_at", -1).limit(10).to_list(10)
        history.reverse()
        
        ai_response = await openai_service.generate_sms_reply(
            tenant_name=tenant["name"],
            tenant_timezone=tenant.get("timezone", "America/New_York"),
            tone_profile=tenant.get("tone_profile", "PROFESSIONAL"),
            customer_name=customer.get("first_name", "there"),
            conversation_history=history,
            current_message=body,
            context_type="GENERAL"
        )
        
        # Send AI response
        if tenant.get("twilio_phone_number"):
            from services.twilio_service import twilio_service
            
            result = await twilio_service.send_sms(
                to_phone=from_phone,
                body=ai_response,
                from_phone=tenant["twilio_phone_number"]
            )
            
            if result["success"]:
                # Log AI response
                ai_msg = Message(
                    tenant_id=tenant_id,
                    conversation_id=conv["id"],
                    customer_id=customer["id"],
                    direction=MessageDirection.OUTBOUND,
                    sender_type=SenderType.AI,
                    channel=PreferredChannel.SMS,
                    content=ai_response,
                    metadata={"twilio_sid": result.get("provider_message_id")}
                )
                ai_msg_dict = ai_msg.model_dump(mode='json')
                await db.messages.insert_one(ai_msg_dict)
                
                # Update conversation
                await db.conversations.update_one(
                    {"id": conv["id"]},
                    {"$set": {
                        "last_message_from": SenderType.AI.value,
                        "last_message_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
    
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
    
    return {"status": "received"}


# ============= DASHBOARD ENDPOINT =============

@v1_router.get("/dashboard")
async def get_dashboard(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get dashboard data for tenant"""
    import pytz
    
    # Get tenant timezone
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")
    
    # Use tenant timezone for date calculations
    now = datetime.now(tenant_tz)
    today_start = tenant_tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = tenant_tz.localize(datetime(now.year, now.month, 1, 0, 0, 0))
    
    # Leads this week
    leads_week = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": week_start.isoformat()}
    })
    
    # Leads this month
    leads_month = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": month_start.isoformat()}
    })
    
    # Jobs this week
    jobs_week = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": week_start.isoformat()}
    })
    
    # Jobs today
    jobs_today = await db.jobs.find({
        "tenant_id": tenant_id,
        "service_window_start": {
            "$gte": today_start.isoformat(),
            "$lt": (today_start + timedelta(days=1)).isoformat()
        }
    }, {"_id": 0}).to_list(50)
    
    # Jobs tomorrow
    tomorrow_start = today_start + timedelta(days=1)
    jobs_tomorrow = await db.jobs.find({
        "tenant_id": tenant_id,
        "service_window_start": {
            "$gte": tomorrow_start.isoformat(),
            "$lt": (tomorrow_start + timedelta(days=1)).isoformat()
        }
    }, {"_id": 0}).to_list(50)
    
    # Recent leads
    recent_leads = await db.leads.find(
        {"tenant_id": tenant_id}, {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    # Leads by source (last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    leads_by_source = await db.leads.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": thirty_days_ago.isoformat()}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]).to_list(20)
    
    # Jobs by status
    jobs_by_status = await db.jobs.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": thirty_days_ago.isoformat()}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(20)
    
    # Quote conversion
    total_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": month_start.isoformat()}
    })
    accepted_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "status": QuoteStatus.ACCEPTED.value,
        "created_at": {"$gte": month_start.isoformat()}
    })
    
    # Revenue metrics
    # Potential revenue: sum of quote_amount for all scheduled/booked/en_route/on_site jobs this month
    potential_jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": {"$in": ["SCHEDULED", "BOOKED", "EN_ROUTE", "ON_SITE"]},
        "created_at": {"$gte": month_start.isoformat()}
    }, {"_id": 0, "quote_amount": 1}).to_list(1000)
    potential_revenue = sum(j.get("quote_amount", 0) or 0 for j in potential_jobs)
    
    # Completed revenue: sum of quote_amount for completed jobs this month
    completed_jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": "COMPLETED",
        "created_at": {"$gte": month_start.isoformat()}
    }, {"_id": 0, "quote_amount": 1}).to_list(1000)
    completed_revenue = sum(j.get("quote_amount", 0) or 0 for j in completed_jobs)
    
    # Also add invoice revenue for comparison
    paid_invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": "PAID",
        "created_at": {"$gte": month_start.isoformat()}
    }, {"_id": 0, "amount": 1}).to_list(1000)
    invoiced_revenue = sum(i.get("amount", 0) or 0 for i in paid_invoices)
    
    return {
        "metrics": {
            "leads_this_week": leads_week,
            "leads_this_month": leads_month,
            "jobs_this_week": jobs_week,
            "quote_conversion": round(accepted_quotes / total_quotes * 100, 1) if total_quotes > 0 else 0,
            "potential_revenue": round(potential_revenue, 2),
            "completed_revenue": round(completed_revenue, 2),
            "invoiced_revenue": round(invoiced_revenue, 2),
            "total_estimated_revenue": round(potential_revenue + completed_revenue, 2)
        },
        "jobs_today": serialize_docs(jobs_today),
        "jobs_tomorrow": serialize_docs(jobs_tomorrow),
        "recent_leads": serialize_docs(recent_leads),
        "charts": {
            "leads_by_source": {item["_id"]: item["count"] for item in leads_by_source},
            "jobs_by_status": {item["_id"]: item["count"] for item in jobs_by_status}
        }
    }


# ============= SETUP DEFAULT SUPERADMIN =============

@app.on_event("startup")
async def startup_event():
    """Initialize optional bootstrap admin and scheduler."""
    bootstrap_email = os.environ.get("DEFAULT_SUPERADMIN_EMAIL", "").strip().lower()
    bootstrap_password = os.environ.get("DEFAULT_SUPERADMIN_PASSWORD", "").strip()
    bootstrap_name = os.environ.get("DEFAULT_SUPERADMIN_NAME", "Platform Admin").strip() or "Platform Admin"

    # Bootstrap is opt-in to avoid hardcoded credentials in source code.
    if bootstrap_email and bootstrap_password:
        superadmin = await db.users.find_one({"email": bootstrap_email})
        if not superadmin:
            user_id = str(uuid4())
            admin_dict = {
                "id": user_id,
                "email": bootstrap_email,
                "password_hash": hash_password(bootstrap_password),
                "name": bootstrap_name,
                "role": UserRole.SUPERADMIN.value,
                "status": UserStatus.ACTIVE.value,
                "tenant_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(admin_dict)
            logger.info(f"Created bootstrap superadmin: {bootstrap_email}")
    elif bootstrap_email or bootstrap_password:
        logger.warning("DEFAULT_SUPERADMIN bootstrap skipped: both email and password must be set")

    # Initialize background scheduler
    try:
        from scheduler import init_scheduler
        init_scheduler()
        logger.info("Background scheduler initialized")
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")


# ============= DISPATCH BOARD ENDPOINTS =============

@v1_router.get("/dispatch/board")
async def get_dispatch_board(
    date: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get dispatch board data - jobs and technicians for a day"""
    import pytz
    
    # Get tenant timezone
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_tz_str = tenant.get("timezone", "America/New_York") if tenant else "America/New_York"
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")
    
    # Default to today in tenant timezone
    if not date:
        date = datetime.now(tenant_tz).strftime("%Y-%m-%d")
    
    # Parse date and create timezone-aware bounds
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        # Make timezone aware in tenant timezone
        date_start = tenant_tz.localize(target_date.replace(hour=0, minute=0, second=0))
        date_end = date_start + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Get jobs for the day
    jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "service_window_start": {
            "$gte": date_start.isoformat(),
            "$lt": date_end.isoformat()
        },
        "status": {"$nin": ["CANCELLED"]}
    }).to_list(100)
    
    # Enrich jobs with customer and property info
    for job in jobs:
        customer = await db.customers.find_one({"id": job.get("customer_id")}, {"_id": 0})
        prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
        job["customer"] = serialize_doc(customer) if customer else None
        job["property"] = serialize_doc(prop) if prop else None
    
    # Get all active technicians
    technicians = await db.technicians.find({
        "tenant_id": tenant_id,
        "active": True
    }, {"_id": 0}).to_list(50)
    
    # Group jobs by technician
    unassigned_jobs = []
    assigned_jobs = {}
    
    for job in jobs:
        tech_id = job.get("assigned_technician_id")
        if tech_id:
            if tech_id not in assigned_jobs:
                assigned_jobs[tech_id] = []
            assigned_jobs[tech_id].append(serialize_doc(job))
        else:
            unassigned_jobs.append(serialize_doc(job))
    
    # Merge assigned jobs into technician objects
    technicians_with_jobs = []
    for tech in technicians:
        tech_data = serialize_doc(tech)
        tech_data["jobs"] = assigned_jobs.get(tech["id"], [])
        technicians_with_jobs.append(tech_data)
    
    return {
        "date": date,
        "technicians": technicians_with_jobs,
        "unassigned_jobs": unassigned_jobs,
        "assigned_jobs": assigned_jobs,
        "summary": {
            "total_jobs": len(jobs),
            "unassigned": len(unassigned_jobs),
            "assigned": len(jobs) - len(unassigned_jobs)
        }
    }


@v1_router.post("/dispatch/assign")
async def assign_job_to_tech(
    job_id: str,
    technician_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Assign or unassign a job to a technician"""
    # Verify job exists
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify technician if assigning
    if technician_id:
        tech = await db.technicians.find_one({"id": technician_id, "tenant_id": tenant_id})
        if not tech:
            raise HTTPException(status_code=404, detail="Technician not found")
    
    # Update job
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "assigned_technician_id": technician_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"success": True, "job_id": job_id, "technician_id": technician_id}


# ============= ANALYTICS/REPORTS ENDPOINTS =============

@v1_router.get("/analytics/overview")
async def get_analytics_overview(
    period: str = "30d",
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive analytics overview"""
    # Calculate date range
    now = datetime.now(timezone.utc)
    if period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=30)
    
    start_str = start_date.isoformat()
    
    # Lead metrics
    total_leads = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_str}
    })
    
    leads_by_status = await db.leads.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": start_str}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(20)
    
    leads_by_source = await db.leads.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": start_str}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]).to_list(20)
    
    # Job metrics
    total_jobs = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_str}
    })
    
    jobs_by_status = await db.jobs.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": start_str}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(20)
    
    jobs_by_type = await db.jobs.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": start_str}}},
        {"$group": {"_id": "$job_type", "count": {"$sum": 1}}}
    ]).to_list(20)
    
    completed_jobs = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "status": "COMPLETED",
        "created_at": {"$gte": start_str}
    })
    
    # Quote metrics
    total_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_str}
    })
    
    accepted_quotes = await db.quotes.count_documents({
        "tenant_id": tenant_id,
        "status": "ACCEPTED",
        "created_at": {"$gte": start_str}
    })
    
    # Revenue from accepted quotes
    revenue_pipeline = [
        {"$match": {
            "tenant_id": tenant_id,
            "status": "ACCEPTED",
            "created_at": {"$gte": start_str}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    revenue_result = await db.quotes.aggregate(revenue_pipeline).to_list(1)
    quote_revenue = revenue_result[0]["total"] if revenue_result else 0
    
    # Revenue from jobs (quote_amount field)
    # Potential revenue: booked/scheduled jobs
    potential_jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": {"$in": ["SCHEDULED", "BOOKED", "EN_ROUTE", "ON_SITE"]},
        "created_at": {"$gte": start_str}
    }, {"_id": 0, "quote_amount": 1}).to_list(1000)
    potential_revenue = sum(j.get("quote_amount", 0) or 0 for j in potential_jobs)
    
    # Completed revenue: completed jobs
    completed_jobs_revenue = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": "COMPLETED",
        "created_at": {"$gte": start_str}
    }, {"_id": 0, "quote_amount": 1}).to_list(1000)
    job_completed_revenue = sum(j.get("quote_amount", 0) or 0 for j in completed_jobs_revenue)
    
    # Invoiced (paid) revenue
    paid_invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": "PAID",
        "created_at": {"$gte": start_str}
    }, {"_id": 0, "amount": 1}).to_list(1000)
    invoiced_revenue = sum(i.get("amount", 0) or 0 for i in paid_invoices)
    
    # Total revenue is the higher of invoiced or completed job revenue (to avoid double counting)
    total_revenue = max(invoiced_revenue, job_completed_revenue, quote_revenue)
    
    # Daily trends (last 14 days)
    daily_trends = []
    for i in range(14):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_leads = await db.leads.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })
        
        day_jobs = await db.jobs.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })
        
        daily_trends.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "leads": day_leads,
            "jobs": day_jobs
        })
    
    daily_trends.reverse()
    
    # Conversion rates
    leads_converted = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "status": "JOB_BOOKED",
        "created_at": {"$gte": start_str}
    })
    
    lead_conversion_rate = round(leads_converted / total_leads * 100, 1) if total_leads > 0 else 0
    quote_conversion_rate = round(accepted_quotes / total_quotes * 100, 1) if total_quotes > 0 else 0
    job_completion_rate = round(completed_jobs / total_jobs * 100, 1) if total_jobs > 0 else 0
    
    # Technician performance
    tech_performance = await db.jobs.aggregate([
        {"$match": {
            "tenant_id": tenant_id,
            "status": "COMPLETED",
            "assigned_technician_id": {"$ne": None},
            "created_at": {"$gte": start_str}
        }},
        {"$group": {
            "_id": "$assigned_technician_id",
            "completed_jobs": {"$sum": 1}
        }}
    ]).to_list(20)
    
    # Enrich with tech names
    for perf in tech_performance:
        tech = await db.technicians.find_one({"id": perf["_id"]}, {"_id": 0, "name": 1})
        perf["technician_name"] = tech["name"] if tech else "Unknown"
    
    return {
        "period": period,
        "summary": {
            "total_leads": total_leads,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "total_quotes": total_quotes,
            "accepted_quotes": accepted_quotes,
            "total_revenue": round(total_revenue, 2),
            "potential_revenue": round(potential_revenue, 2),
            "job_completed_revenue": round(job_completed_revenue, 2),
            "invoiced_revenue": round(invoiced_revenue, 2)
        },
        "conversion_rates": {
            "lead_to_job": lead_conversion_rate,
            "quote_acceptance": quote_conversion_rate,
            "job_completion": job_completion_rate
        },
        "leads": {
            "by_status": {item["_id"]: item["count"] for item in leads_by_status},
            "by_source": {item["_id"]: item["count"] for item in leads_by_source}
        },
        "jobs": {
            "by_status": {item["_id"]: item["count"] for item in jobs_by_status},
            "by_type": {item["_id"]: item["count"] for item in jobs_by_type}
        },
        "daily_trends": daily_trends,
        "technician_performance": tech_performance
    }


# ============= CUSTOMER PORTAL ENDPOINTS =============

async def generate_portal_token(customer_id: str, tenant_id: str) -> str:
    """Generate a portal access token for a customer"""
    import hashlib
    import secrets
    
    # Create a simple token (in production, use proper JWT)
    random_part = secrets.token_urlsafe(16)
    token = f"{customer_id[:8]}-{random_part}"
    
    # Store token in customer record
    await db.customers.update_one(
        {"id": customer_id, "tenant_id": tenant_id},
        {"$set": {"portal_token": token, "portal_token_created": datetime.now(timezone.utc).isoformat()}}
    )
    
    return token


@v1_router.post("/portal/generate-link")
async def generate_portal_link(
    customer_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Generate a customer portal link"""
    customer = await db.customers.find_one({"id": customer_id, "tenant_id": tenant_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    token = await generate_portal_token(customer_id, tenant_id)
    base_url = os.environ.get('APP_BASE_URL', 'http://localhost:3000')
    portal_url = f"{base_url}/portal/{token}"
    
    return {
        "success": True,
        "portal_url": portal_url,
        "token": token
    }


@v1_router.get("/portal/{token}")
async def get_portal_data(token: str):
    """Get customer portal data (public endpoint)"""
    # Find customer by token
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    tenant_id = customer["tenant_id"]
    customer_id = customer["id"]
    
    # Get tenant info
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "name": 1, "primary_phone": 1})
    
    # Get upcoming jobs
    now = datetime.now(timezone.utc)
    upcoming_jobs = await db.jobs.find({
        "customer_id": customer_id,
        "status": {"$in": ["BOOKED", "EN_ROUTE"]},
        "service_window_start": {"$gte": now.isoformat()}
    }, {"_id": 0}).sort("service_window_start", 1).to_list(10)
    
    # Enrich with property info
    for job in upcoming_jobs:
        prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0})
        job["property"] = serialize_doc(prop) if prop else None
        # Get technician if assigned
        if job.get("assigned_technician_id"):
            tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0, "name": 1, "phone": 1})
            job["technician"] = serialize_doc(tech) if tech else None
    
    # Get past jobs
    past_jobs = await db.jobs.find({
        "customer_id": customer_id,
        "status": "COMPLETED"
    }, {"_id": 0}).sort("service_window_start", -1).limit(5).to_list(5)
    
    # Get pending quotes
    pending_quotes = await db.quotes.find({
        "customer_id": customer_id,
        "status": {"$in": ["DRAFT", "SENT"]}
    }, {"_id": 0}).to_list(10)
    
    # Enrich quotes with property info
    for quote in pending_quotes:
        prop = await db.properties.find_one({"id": quote.get("property_id")}, {"_id": 0})
        quote["property"] = serialize_doc(prop) if prop else None
    
    # Get properties
    properties = await db.properties.find({
        "customer_id": customer_id
    }, {"_id": 0}).to_list(20)
    
    # Get pending invoices (unpaid)
    pending_invoices = await db.invoices.find({
        "customer_id": customer_id,
        "status": {"$in": ["DRAFT", "SENT", "PARTIALLY_PAID", "OVERDUE"]}
    }, {"_id": 0}).to_list(10)
    
    # Enrich invoices with job info
    for invoice in pending_invoices:
        job = await db.jobs.find_one({"id": invoice.get("job_id")}, {"_id": 0, "job_type": 1, "service_window_start": 1})
        invoice["job"] = serialize_doc(job) if job else None
    
    # Get reviews by customer
    reviews = await db.reviews.find({
        "customer_id": customer_id
    }, {"_id": 0}).to_list(20)
    
    # Enrich past jobs with review status
    for job in past_jobs:
        existing_review = await db.reviews.find_one({"job_id": job["id"]}, {"_id": 0})
        job["review"] = serialize_doc(existing_review) if existing_review else None
    
    return {
        "customer": {
            "first_name": customer.get("first_name"),
            "last_name": customer.get("last_name"),
            "phone": customer.get("phone"),
            "email": customer.get("email")
        },
        "company": tenant,
        "upcoming_appointments": serialize_docs(upcoming_jobs),
        "past_appointments": serialize_docs(past_jobs),
        "pending_quotes": serialize_docs(pending_quotes),
        "pending_invoices": serialize_docs(pending_invoices),
        "properties": serialize_docs(properties),
        "reviews": serialize_docs(reviews)
    }


@v1_router.post("/portal/{token}/quote/{quote_id}/respond")
async def respond_to_quote(token: str, quote_id: str, action: str):
    """Customer responds to a quote (accept/decline)"""
    # Verify token
    customer = await db.customers.find_one({"portal_token": token})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    # Get quote
    quote = await db.quotes.find_one({"id": quote_id, "customer_id": customer["id"]})
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    if action == "accept":
        new_status = "ACCEPTED"
        update_field = "accepted_at"
    elif action == "decline":
        new_status = "DECLINED"
        update_field = "declined_at"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    await db.quotes.update_one(
        {"id": quote_id},
        {"$set": {
            "status": new_status,
            update_field: datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"success": True, "status": new_status}


@v1_router.post("/portal/{token}/reschedule-request")
async def request_reschedule(token: str, job_id: str, message: str):
    """Customer requests to reschedule an appointment"""
    # Verify token
    customer = await db.customers.find_one({"portal_token": token})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    # Get job
    job = await db.jobs.find_one({"id": job_id, "customer_id": customer["id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Create a message/note for staff
    tenant_id = customer["tenant_id"]
    
    # Find or create conversation
    conv = await db.conversations.find_one({
        "customer_id": customer["id"],
        "tenant_id": tenant_id,
        "status": "OPEN"
    })
    
    if not conv:
        conv = {
            "id": str(__import__('uuid').uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer["id"],
            "primary_channel": "SMS",
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.conversations.insert_one(conv)
    
    # Create message
    msg = {
        "id": str(__import__('uuid').uuid4()),
        "tenant_id": tenant_id,
        "conversation_id": conv["id"],
        "customer_id": customer["id"],
        "direction": "INBOUND",
        "sender_type": "CUSTOMER",
        "channel": "SMS",
        "content": f"[Portal] Reschedule Request for job {job_id}: {message}",
        "is_call_summary": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.messages.insert_one(msg)
    
    # Update conversation
    await db.conversations.update_one(
        {"id": conv["id"]},
        {"$set": {
            "last_message_from": "CUSTOMER",
            "last_message_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"success": True, "message": "Reschedule request submitted"}


@v1_router.post("/portal/{token}/review")
async def submit_review(token: str, job_id: str, rating: int, comment: Optional[str] = None):
    """Customer submits a review for a completed job"""
    # Verify token
    customer = await db.customers.find_one({"portal_token": token})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Get job
    job = await db.jobs.find_one({"id": job_id, "customer_id": customer["id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if job is completed
    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Can only review completed jobs")
    
    # Check if already reviewed
    existing_review = await db.reviews.find_one({"job_id": job_id, "customer_id": customer["id"]})
    if existing_review:
        raise HTTPException(status_code=400, detail="Job already reviewed")
    
    # Create review
    review = {
        "id": str(__import__('uuid').uuid4()),
        "tenant_id": customer["tenant_id"],
        "customer_id": customer["id"],
        "job_id": job_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.reviews.insert_one(review)
    
    return {"success": True, "review_id": review["id"]}


@v1_router.post("/portal/{token}/add-note")
async def add_customer_note(token: str, note: str, job_id: Optional[str] = None):
    """Customer adds a note (general or for a specific job)"""
    # Verify token
    customer = await db.customers.find_one({"portal_token": token})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    tenant_id = customer["tenant_id"]
    
    # If job_id is provided, verify it belongs to customer
    if job_id:
        job = await db.jobs.find_one({"id": job_id, "customer_id": customer["id"]})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    
    # Find or create conversation
    conv = await db.conversations.find_one({
        "customer_id": customer["id"],
        "tenant_id": tenant_id,
        "status": "OPEN"
    })
    
    if not conv:
        conv = {
            "id": str(__import__('uuid').uuid4()),
            "tenant_id": tenant_id,
            "customer_id": customer["id"],
            "primary_channel": "SMS",
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.conversations.insert_one(conv)
    
    # Create message as a note
    note_content = f"[Portal Note]"
    if job_id:
        note_content += f" (Job: {job_id})"
    note_content += f": {note}"
    
    msg = {
        "id": str(__import__('uuid').uuid4()),
        "tenant_id": tenant_id,
        "conversation_id": conv["id"],
        "customer_id": customer["id"],
        "direction": "INBOUND",
        "sender_type": "CUSTOMER",
        "channel": "SMS",
        "content": note_content,
        "is_call_summary": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.messages.insert_one(msg)
    
    # Update conversation
    await db.conversations.update_one(
        {"id": conv["id"]},
        {"$set": {
            "last_message_from": "CUSTOMER",
            "last_message_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"success": True, "message": "Note added successfully"}


# ============= SEND PORTAL LINK VIA SMS =============

@v1_router.post("/customers/{customer_id}/send-portal-link")
async def send_portal_link_sms(
    customer_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Generate and send portal link to customer via SMS"""
    customer = await db.customers.find_one({"id": customer_id, "tenant_id": tenant_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    
    # Generate token
    token = await generate_portal_token(customer_id, tenant_id)
    base_url = os.environ.get('APP_BASE_URL', 'http://localhost:3000')
    portal_url = f"{base_url}/portal/{token}"
    
    # Send SMS
    from services.twilio_service import twilio_service
    
    message = f"Hi {customer['first_name']}! View your appointments and quotes with {tenant['name']}: {portal_url}"
    
    result = await twilio_service.send_sms(
        to_phone=customer['phone'],
        body=message
    )
    
    return {
        "success": result.get("success", False),
        "portal_url": portal_url,
        "error": result.get("error")
    }


# ============= MANUAL REMINDER TRIGGER =============

@v1_router.post("/jobs/{job_id}/send-reminder")
async def send_manual_reminder(
    job_id: str,
    reminder_type: str = "day_before",
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Manually send a reminder for a job"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    
    if not customer or not tenant:
        raise HTTPException(status_code=404, detail="Customer or tenant not found")
    
    from scheduler import send_reminder_sms
    success = await send_reminder_sms(tenant, customer, job, reminder_type)
    
    if success:
        # Update the appropriate flag
        flag_field = f"reminder_{reminder_type}_sent"
        await db.jobs.update_one(
            {"id": job_id},
            {"$set": {flag_field: True}}
        )
    
    return {"success": success}


# ============= BRANDING SETTINGS =============

@v1_router.get("/settings/branding")
async def get_branding_settings(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get tenant branding settings"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Return branding settings or defaults
    branding = tenant.get("branding", {})
    defaults = {
        "logo_url": None,
        "favicon_url": None,
        "primary_color": "#0066CC",
        "secondary_color": "#004499",
        "accent_color": "#FF6600",
        "text_on_primary": "#FFFFFF",
        "font_family": "Inter",
        "email_from_name": tenant.get("name"),
        "email_reply_to": tenant.get("primary_contact_email"),
        "sms_sender_name": None,
        "portal_title": f"{tenant.get('name')} Customer Portal",
        "portal_welcome_message": "Welcome to your customer portal",
        "portal_support_email": tenant.get("primary_contact_email"),
        "portal_support_phone": tenant.get("primary_phone"),
        "custom_domain": None,
        "custom_domain_verified": False,
        "white_label_enabled": False
    }
    
    # Merge defaults with stored settings
    result = {**defaults, **branding}
    return result


@v1_router.put("/settings/branding")
async def update_branding_settings(
    branding: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update tenant branding settings"""
    # Validate required fields
    allowed_fields = [
        "logo_url", "favicon_url", "primary_color", "secondary_color",
        "accent_color", "text_on_primary", "font_family",
        "email_from_name", "email_reply_to", "sms_sender_name",
        "portal_title", "portal_welcome_message", "portal_support_email", "portal_support_phone",
        "custom_domain", "white_label_enabled"
    ]
    
    # Filter to only allowed fields
    filtered_branding = {k: v for k, v in branding.items() if k in allowed_fields}
    
    await db.tenants.update_one(
        {"id": tenant_id},
        {
            "$set": {
                "branding": filtered_branding,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"success": True, "branding": filtered_branding}


# ============= REVIEW SETTINGS =============

@v1_router.get("/settings/reviews")
async def get_review_settings(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get tenant review request settings"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant.get("review_settings") or {}


@v1_router.put("/settings/reviews")
async def update_review_settings(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update tenant review request settings"""
    allowed = [
        "enabled", "delay_hours", "google_review_url", "yelp_review_url",
        "facebook_review_url", "preferred_platform", "message_template"
    ]
    filtered = {k: v for k, v in data.items() if k in allowed}
    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {"review_settings": filtered, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True, "review_settings": filtered}


# Custom Fields endpoints
@v1_router.get("/settings/custom-fields")
async def get_custom_fields(tenant_id: str = Depends(get_tenant_id), current_user: dict = Depends(get_current_user)):
    """Get tenant's custom field definitions"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"custom_fields": tenant.get("custom_fields", [])}

@v1_router.post("/settings/custom-fields")
async def create_custom_field(data: dict, tenant_id: str = Depends(get_tenant_id), current_user: dict = Depends(get_current_user)):
    """Create a new custom field"""
    if current_user.get("role") not in ["OWNER", "ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    field = {
        "id": str(uuid4()),
        "name": data.get("name"),
        "slug": data.get("slug", data.get("name", "").lower().replace(" ", "_")),
        "type": data.get("type", "TEXT"),  # TEXT, NUMBER, SELECT, MULTISELECT, DATE, BOOLEAN
        "options": data.get("options", []),
        "applies_to": data.get("applies_to", "job"),  # job, customer, property
        "required": data.get("required", False),
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await db.tenants.update_one(
        {"id": tenant_id},
        {"$push": {"custom_fields": field}}
    )
    return {"success": True, "field": field}

@v1_router.put("/settings/custom-fields/{field_id}")
async def update_custom_field(field_id: str, data: dict, tenant_id: str = Depends(get_tenant_id), current_user: dict = Depends(get_current_user)):
    """Update a custom field"""
    if current_user.get("role") not in ["OWNER", "ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    update_data = {k: v for k, v in data.items() if k not in ["id", "created_at"]}

    result = await db.tenants.update_one(
        {"id": tenant_id, "custom_fields.id": field_id},
        {"$set": {f"custom_fields.$.{k}": v for k, v in update_data.items()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Custom field not found")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    field = next((f for f in tenant.get("custom_fields", []) if f["id"] == field_id), None)
    return {"success": True, "field": field}

@v1_router.delete("/settings/custom-fields/{field_id}")
async def delete_custom_field(field_id: str, tenant_id: str = Depends(get_tenant_id), current_user: dict = Depends(get_current_user)):
    """Delete a custom field"""
    if current_user.get("role") not in ["OWNER", "ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.tenants.update_one(
        {"id": tenant_id},
        {"$pull": {"custom_fields": {"id": field_id}}}
    )
    return {"success": True}

@v1_router.get("/settings/industry")
async def get_industry_settings(tenant_id: str = Depends(get_tenant_id), current_user: dict = Depends(get_current_user)):
    """Get tenant's industry settings"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {
        "industry_slug": tenant.get("industry_slug", ""),
        "custom_job_types": tenant.get("custom_job_types", []),
        "disabled_job_types": tenant.get("disabled_job_types", [])
    }

@v1_router.put("/settings/industry")
async def update_industry_settings(data: dict, tenant_id: str = Depends(get_tenant_id), current_user: dict = Depends(get_current_user)):
    """Update tenant's industry settings"""
    if current_user.get("role") not in ["OWNER", "ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    update = {}
    if "industry_slug" in data:
        update["industry_slug"] = data["industry_slug"]
        update["onboarding_completed"] = True
    if "custom_job_types" in data:
        update["custom_job_types"] = data["custom_job_types"]
    if "disabled_job_types" in data:
        update["disabled_job_types"] = data["disabled_job_types"]

    if update:
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.tenants.update_one({"id": tenant_id}, {"$set": update})

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    return {
        "industry_slug": tenant.get("industry_slug", ""),
        "custom_job_types": tenant.get("custom_job_types", []),
        "disabled_job_types": tenant.get("disabled_job_types", [])
    }


@v1_router.get("/reviews/pending")
async def get_pending_reviews(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get jobs that have review requests scheduled but not yet sent"""
    jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": "COMPLETED",
        "review_scheduled_at": {"$exists": True},
        "review_request_sent": {"$ne": True},
    }, {"_id": 0}).to_list(200)
    return serialize_docs(jobs)


@v1_router.get("/reviews/stats")
async def get_review_stats(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get review request statistics"""
    total_completed = await db.jobs.count_documents({"tenant_id": tenant_id, "status": "COMPLETED"})
    total_requested = await db.jobs.count_documents({"tenant_id": tenant_id, "review_request_sent": True})
    pending = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "status": "COMPLETED",
        "review_scheduled_at": {"$exists": True},
        "review_request_sent": {"$ne": True},
    })
    return {
        "total_completed": total_completed,
        "review_requests_sent": total_requested,
        "pending_review_requests": pending,
        "request_rate": round(total_requested / total_completed * 100, 1) if total_completed else 0,
    }


# ============= PUBLIC TRACKING =============

@api_router.get("/track/{token}")
async def get_tracking_info(token: str):
    """Public tracking page - no auth required"""
    job = await db.jobs.find_one({"tracking_token": token}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Tracking link not found or expired")

    tenant = await db.tenants.find_one({"id": job["tenant_id"]}, {"_id": 0})
    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    prop = await db.properties.find_one({"id": job.get("property_id")}, {"_id": 0}) if job.get("property_id") else None
    tech = None
    if job.get("assigned_technician_id"):
        tech_doc = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0})
        if tech_doc:
            tech = {"name": tech_doc.get("name"), "photo_url": tech_doc.get("photo_url"), "vehicle_info": tech_doc.get("vehicle_info")}

    minutes_remaining = None
    if job.get("estimated_arrival"):
        try:
            eta = datetime.fromisoformat(job["estimated_arrival"].replace("Z", "+00:00"))
            diff = (eta - datetime.now(timezone.utc)).total_seconds() / 60
            minutes_remaining = max(0, int(diff))
        except Exception:
            pass

    return {
        "status": job.get("status"),
        "job_type": job.get("job_type"),
        "service_window_start": job.get("service_window_start"),
        "service_window_end": job.get("service_window_end"),
        "en_route_at": job.get("en_route_at"),
        "estimated_arrival": job.get("estimated_arrival"),
        "actual_arrival": job.get("actual_arrival"),
        "minutes_remaining": minutes_remaining,
        "technician": tech,
        "company": {
            "name": tenant.get("name") if tenant else None,
            "phone": tenant.get("primary_phone") if tenant else None,
            "logo_url": (tenant.get("branding") or {}).get("logo_url") if tenant else None,
        },
        "property_address": (
            f"{prop.get('address_line1', '')}, {prop.get('city', '')}, {prop.get('state', '')}"
            if prop else None
        ),
        "customer_first_name": customer.get("first_name") if customer else None,
    }


# ============= ENHANCED CUSTOMER PORTAL =============

@v1_router.get("/portal/{token}/branding")
async def get_portal_branding(token: str):
    """Get branding for customer portal (public endpoint)"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    tenant = await db.tenants.find_one({"id": customer["tenant_id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    branding = tenant.get("branding", {})
    defaults = {
        "logo_url": None,
        "company_name": tenant.get("name"),
        "primary_color": "#0066CC",
        "secondary_color": "#004499",
        "accent_color": "#FF6600",
        "text_on_primary": "#FFFFFF",
        "portal_title": f"{tenant.get('name')} Customer Portal",
        "portal_welcome_message": "Welcome to your customer portal",
        "portal_support_email": tenant.get("primary_contact_email"),
        "portal_support_phone": tenant.get("primary_phone"),
        "white_label_enabled": False
    }
    
    result = {**defaults}
    for key in defaults:
        if key in branding and branding[key]:
            result[key] = branding[key]
    
    return result


@v1_router.get("/portal/{token}/messages")
async def get_portal_messages(token: str, limit: int = 50):
    """Get conversation messages for customer portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    # Find conversation
    conversation = await db.conversations.find_one(
        {"customer_id": customer["id"]},
        {"_id": 0}
    )
    
    if not conversation:
        return {"conversation": None, "messages": []}
    
    # Get messages
    messages = await db.messages.find(
        {"conversation_id": conversation["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Reverse to get chronological order
    messages.reverse()
    
    return {
        "conversation": serialize_doc(conversation),
        "messages": serialize_docs(messages)
    }


@v1_router.post("/portal/{token}/request-service")
async def portal_request_service(
    token: str,
    issue_description: str,
    urgency: str = "ROUTINE",
    property_id: Optional[str] = None,
    preferred_date: Optional[str] = None,
    preferred_time_slot: Optional[str] = None
):
    """Customer requests service from portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    tenant_id = customer["tenant_id"]
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    
    # Validate urgency
    valid_urgencies = ["EMERGENCY", "URGENT", "ROUTINE"]
    if urgency not in valid_urgencies:
        urgency = "ROUTINE"
    
    # Create service request record
    service_request = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "issue_description": issue_description,
        "urgency": urgency,
        "preferred_date": preferred_date,
        "preferred_time_slot": preferred_time_slot,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.service_requests.insert_one(service_request)
    
    # Also create a lead from this request
    lead = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "source": "PORTAL_REQUEST",
        "channel": "FORM",
        "status": "NEW",
        "issue_type": issue_description[:100] if len(issue_description) > 100 else issue_description,
        "urgency": urgency,
        "description": issue_description,
        "caller_name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
        "caller_phone": customer.get("phone"),
        "tags": ["portal_request"],
        "first_contact_at": datetime.now(timezone.utc).isoformat(),
        "last_activity_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.leads.insert_one(lead)
    
    # Send confirmation SMS
    from services.twilio_service import twilio_service
    
    confirm_msg = f"Hi {customer.get('first_name')}! We received your service request. A team member will contact you shortly to schedule an appointment."
    if tenant.get("sms_signature"):
        confirm_msg += f" {tenant['sms_signature']}"
    
    await twilio_service.send_sms(
        to_phone=customer["phone"],
        body=confirm_msg
    )
    
    return {
        "success": True,
        "service_request_id": service_request["id"],
        "lead_id": lead["id"],
        "message": "Service request submitted successfully"
    }


@v1_router.get("/portal/{token}/invoices")
async def get_portal_invoices(token: str, status: Optional[str] = None):
    """Get all invoices for customer portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    query = {"customer_id": customer["id"]}
    if status:
        query["status"] = status
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    # Enrich with job info
    for invoice in invoices:
        if invoice.get("job_id"):
            job = await db.jobs.find_one({"id": invoice["job_id"]}, {"_id": 0, "job_type": 1, "service_window_start": 1})
            invoice["job"] = serialize_doc(job) if job else None
        if invoice.get("property_id"):
            prop = await db.properties.find_one({"id": invoice["property_id"]}, {"_id": 0})
            invoice["property"] = serialize_doc(prop) if prop else None
    
    return {"invoices": serialize_docs(invoices)}


@v1_router.get("/portal/{token}/service-history")
async def get_portal_service_history(token: str, limit: int = 20):
    """Get full service history for customer portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    # Get all jobs for customer
    jobs = await db.jobs.find(
        {"customer_id": customer["id"]},
        {"_id": 0}
    ).sort("service_window_start", -1).limit(limit).to_list(limit)
    
    # Enrich with property, technician, and review info
    for job in jobs:
        if job.get("property_id"):
            prop = await db.properties.find_one({"id": job["property_id"]}, {"_id": 0})
            job["property"] = serialize_doc(prop) if prop else None
        if job.get("assigned_technician_id"):
            tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0, "name": 1})
            job["technician"] = serialize_doc(tech) if tech else None
        # Check for review
        review = await db.reviews.find_one({"job_id": job["id"]}, {"_id": 0})
        job["review"] = serialize_doc(review) if review else None
        # Check for invoice
        invoice = await db.invoices.find_one({"job_id": job["id"]}, {"_id": 0, "id": 1, "amount": 1, "status": 1})
        job["invoice"] = serialize_doc(invoice) if invoice else None
    
    return {"service_history": serialize_docs(jobs)}


@v1_router.put("/portal/{token}/profile")
async def update_portal_profile(
    token: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None
):
    """Customer updates their profile from portal"""
    customer = await db.customers.find_one({"portal_token": token}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Invalid portal link")
    
    update_data = {}
    if first_name:
        update_data["first_name"] = first_name
    if last_name:
        update_data["last_name"] = last_name
    if email:
        update_data["email"] = email
    if phone:
        # Normalize phone
        update_data["phone"] = normalize_phone_e164(phone)
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.customers.update_one(
            {"id": customer["id"]},
            {"$set": update_data}
        )
    
    # Return updated customer
    updated_customer = await db.customers.find_one({"id": customer["id"]}, {"_id": 0})
    return {
        "success": True,
        "customer": {
            "first_name": updated_customer.get("first_name"),
            "last_name": updated_customer.get("last_name"),
            "email": updated_customer.get("email"),
            "phone": updated_customer.get("phone")
        }
    }


# ============= SERVICE REQUESTS MANAGEMENT =============

@v1_router.get("/service-requests")
async def list_service_requests(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """List service requests from customer portal"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    
    requests = await db.service_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Enrich with customer info
    for req in requests:
        customer = await db.customers.find_one({"id": req.get("customer_id")}, {"_id": 0, "first_name": 1, "last_name": 1, "phone": 1})
        req["customer"] = serialize_doc(customer) if customer else None
    
    return serialize_docs(requests)


@v1_router.post("/service-requests/{request_id}/convert")
async def convert_service_request_to_job(
    request_id: str,
    job_type: str = "DIAGNOSTIC",
    scheduled_date: Optional[str] = None,
    scheduled_time_slot: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Convert a service request to a booked job"""
    service_request = await db.service_requests.find_one(
        {"id": request_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not service_request:
        raise HTTPException(status_code=404, detail="Service request not found")
    
    # Get customer
    customer = await db.customers.find_one({"id": service_request["customer_id"]}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get or use property
    property_id = service_request.get("property_id")
    if not property_id:
        # Find first property for customer
        prop = await db.properties.find_one({"customer_id": customer["id"]}, {"_id": 0})
        if prop:
            property_id = prop["id"]
    
    if not property_id:
        raise HTTPException(status_code=400, detail="No property found for customer")
    
    # Get tenant for timezone
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    import pytz
    tenant_tz = pytz.timezone(tenant.get("timezone", "America/New_York"))
    
    # Determine schedule
    date_to_use = scheduled_date or service_request.get("preferred_date") or (datetime.now(tenant_tz) + timedelta(days=1)).strftime("%Y-%m-%d")
    time_slot = scheduled_time_slot or service_request.get("preferred_time_slot") or "morning"
    
    # Create time window based on slot
    from datetime import datetime as dt
    base_date = dt.strptime(date_to_use, "%Y-%m-%d")
    
    slot_times = {
        "morning": ("08:00", "12:00"),
        "afternoon": ("12:00", "16:00"),
        "evening": ("16:00", "19:00")
    }
    start_time, end_time = slot_times.get(time_slot, ("08:00", "12:00"))
    
    service_window_start = tenant_tz.localize(dt.strptime(f"{date_to_use} {start_time}", "%Y-%m-%d %H:%M"))
    service_window_end = tenant_tz.localize(dt.strptime(f"{date_to_use} {end_time}", "%Y-%m-%d %H:%M"))
    
    # Calculate quote amount
    urgency = service_request.get("urgency", "ROUTINE")
    quote_amount = calculate_quote_amount(job_type, urgency)
    
    # Find or create lead
    lead = await db.leads.find_one({
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "tags": "portal_request"
    }, {"_id": 0})
    
    lead_id = lead["id"] if lead else None
    
    # Create job
    job = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "lead_id": lead_id,
        "job_type": job_type,
        "priority": "EMERGENCY" if urgency == "EMERGENCY" else ("HIGH" if urgency == "URGENT" else "NORMAL"),
        "service_window_start": service_window_start.isoformat(),
        "service_window_end": service_window_end.isoformat(),
        "status": "BOOKED",
        "created_by": "STAFF",
        "notes": service_request.get("issue_description"),
        "quote_amount": quote_amount,
        "reminder_day_before_sent": False,
        "reminder_morning_of_sent": False,
        "en_route_sms_sent": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.jobs.insert_one(job)
    
    # Update service request status
    await db.service_requests.update_one(
        {"id": request_id},
        {"$set": {"status": "CONVERTED_TO_LEAD", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Update lead status if exists
    if lead_id:
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {"status": "JOB_BOOKED", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    # Create quote
    quote = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "job_id": job["id"],
        "amount": quote_amount,
        "currency": "USD",
        "description": f"{job_type} service - {service_request.get('issue_description', '')[:100]}",
        "status": "SENT",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.quotes.insert_one(quote)
    
    # Update job with quote_id
    await db.jobs.update_one({"id": job["id"]}, {"$set": {"quote_id": quote["id"]}})
    
    # Send confirmation SMS
    from services.twilio_service import twilio_service
    
    msg = f"Hi {customer['first_name']}! Your service appointment is confirmed for {base_date.strftime('%A, %B %d')} ({time_slot}). Quote: ${quote_amount:.2f}."
    if tenant.get("sms_signature"):
        msg += f" {tenant['sms_signature']}"
    
    await twilio_service.send_sms(to_phone=customer["phone"], body=msg)
    
    return {
        "success": True,
        "job": serialize_doc(job),
        "quote": serialize_doc(quote)
    }


# ============= INITIAL SETUP (ONE-TIME) =============

@api_router.post("/setup/admin")
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
    password_hash = pwd_context.hash("Finao028!")
    
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


# ============= CONTACT FORM API (PUBLIC) =============

class ContactFormRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    message: str

@api_router.post("/contact")
async def submit_contact_form(request: ContactFormRequest):
    """
    Handle contact form submissions from landing page.
    Saves to MongoDB and sends email notification via Resend.
    """
    import resend
    
    # Save to MongoDB
    contact_id = str(uuid4())
    contact = {
        "id": contact_id,
        "name": request.name,
        "email": request.email,
        "phone": request.phone,
        "company": request.company,
        "message": request.message,
        "status": "NEW",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.contact_submissions.insert_one(contact)
    logger.info(f"Contact form submitted: {contact_id} from {request.email}")
    
    # Send email notification via Resend
    resend_key = os.environ.get('RESEND_API_KEY')
    if resend_key:
        try:
            resend.api_key = resend_key
            
            email_html = f"""
            <h2>New FieldOS Contact Form Submission</h2>
            <p><strong>Name:</strong> {request.name}</p>
            <p><strong>Email:</strong> {request.email}</p>
            <p><strong>Phone:</strong> {request.phone or 'Not provided'}</p>
            <p><strong>Company:</strong> {request.company or 'Not provided'}</p>
            <p><strong>Message:</strong></p>
            <p>{request.message}</p>
            <hr>
            <p><small>Submitted at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</small></p>
            """
            
            resend.Emails.send({
                "from": "FieldOS <noreply@arisolutionsinc.com>",
                "to": ["fieldos@arisolutionsinc.com"],
                "subject": f"New Contact: {request.name} - {request.company or 'FieldOS Inquiry'}",
                "html": email_html
            })
            logger.info(f"Contact notification email sent for {contact_id}")
        except Exception as e:
            logger.error(f"Failed to send contact notification email: {e}")
    
    return {"success": True, "message": "Thank you! We'll be in touch soon."}


# ============= REVENUE REPORTS =============

@v1_router.get("/reports/revenue")
async def get_revenue_report(
    start_date: str = None,
    end_date: str = None,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Get revenue report with payment tracking"""
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d')
    
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "created_at": {"$gte": start_date, "$lte": end_date + "T23:59:59"}
    }, {"_id": 0}).to_list(10000)
    
    total_invoiced = sum(float(inv.get('total', 0)) for inv in invoices)
    total_paid = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') == 'PAID')
    total_outstanding = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') in ['SENT', 'PENDING'])
    total_overdue = sum(float(inv.get('total', 0)) for inv in invoices if inv.get('status') == 'OVERDUE')
    
    jobs = await db.jobs.find({"tenant_id": tenant_id, "created_at": {"$gte": start_date}}, {"_id": 0}).to_list(10000)
    revenue_by_type = {}
    for job in jobs:
        jtype = job.get('job_type', 'OTHER')
        revenue_by_type[jtype] = revenue_by_type.get(jtype, 0) + float(job.get('quoted_amount', 0))
    
    daily_revenue = {}
    for inv in invoices:
        if inv.get('status') == 'PAID' and inv.get('paid_at'):
            day = inv['paid_at'][:10]
            daily_revenue[day] = daily_revenue.get(day, 0) + float(inv.get('total', 0))
    
    return {
        "period": {"start": start_date, "end": end_date},
        "summary": {
            "total_invoiced": round(total_invoiced, 2),
            "total_paid": round(total_paid, 2),
            "total_outstanding": round(total_outstanding, 2),
            "total_overdue": round(total_overdue, 2),
            "collection_rate": round(total_paid / total_invoiced * 100, 1) if total_invoiced > 0 else 0
        },
        "invoices_count": {
            "total": len(invoices),
            "paid": len([i for i in invoices if i.get('status') == 'PAID']),
            "outstanding": len([i for i in invoices if i.get('status') in ['SENT', 'PENDING']]),
            "overdue": len([i for i in invoices if i.get('status') == 'OVERDUE'])
        },
        "revenue_by_job_type": revenue_by_type,
        "daily_revenue": dict(sorted(daily_revenue.items()))
    }


# ============= INDUSTRY TEMPLATES =============

INDUSTRY_TEMPLATES = {
    "hvac": {"name": "HVAC", "job_types": ["AC Repair", "Heating Repair", "AC Installation", "Furnace Installation", "Maintenance", "Duct Cleaning"], "default_greeting": "Thank you for calling. How can I help with your heating or cooling needs today?"},
    "plumbing": {"name": "Plumbing", "job_types": ["Leak Repair", "Drain Cleaning", "Water Heater", "Toilet Repair", "Faucet Install", "Pipe Repair"], "default_greeting": "Thank you for calling. What plumbing issue can I help you with today?"},
    "electrical": {"name": "Electrical", "job_types": ["Outlet Repair", "Panel Upgrade", "Wiring", "Lighting Install", "Generator", "EV Charger"], "default_greeting": "Thank you for calling. What electrical issue can I help you with?"},
    "landscaping": {"name": "Landscaping", "job_types": ["Lawn Care", "Tree Service", "Irrigation", "Hardscape", "Design", "Seasonal Cleanup"], "default_greeting": "Thank you for calling. How can I help with your landscaping needs?"},
    "cleaning": {"name": "Cleaning", "job_types": ["Regular Cleaning", "Deep Clean", "Move-In/Out", "Post-Construction", "Carpet Cleaning"], "default_greeting": "Thank you for calling. What type of cleaning service are you looking for?"},
    "general": {"name": "General Contractor", "job_types": ["Repair", "Installation", "Maintenance", "Inspection", "Consultation"], "default_greeting": "Thank you for calling. How can I help you today?"}
}

@v1_router.get("/templates/industries")
async def get_industry_templates():
    return INDUSTRY_TEMPLATES

@v1_router.get("/templates/industries/{industry}")
async def get_industry_template(industry: str):
    if industry not in INDUSTRY_TEMPLATES:
        raise HTTPException(status_code=404, detail="Industry template not found")
    return INDUSTRY_TEMPLATES[industry]


# ============= HEALTH CHECK =============

@api_router.get("/")
async def root():
    return {"message": "FieldOS API v1.0.0", "status": "healthy"}


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# Initialize and include modular routes
from routes.admin import router as admin_router, init_admin_routes
from routes.billing import router as billing_router
from routes.integrations import router as integrations_router

# Initialize route dependencies
init_admin_routes(db, require_superadmin, serialize_doc, serialize_docs, hash_password, UserRole, UserStatus, User, Tenant)

# Include routers
v1_router.include_router(admin_router)
v1_router.include_router(billing_router)
v1_router.include_router(integrations_router)

api_router.include_router(v1_router)
app.include_router(api_router)

configure_cors(app)

@app.on_event("shutdown")
async def shutdown_db_client():
    await shutdown_resources(client)
