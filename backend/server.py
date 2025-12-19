"""
FieldOS Backend - Main FastAPI Application
Multi-tenant Revenue & Operations OS for field service companies
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from uuid import uuid4

from models import (
    # Enums
    UserRole, UserStatus, LeadSource, LeadChannel, LeadStatus, Urgency,
    JobType, JobPriority, JobStatus, JobCreatedBy, QuoteStatus, InvoiceStatus,
    ConversationStatus, MessageDirection, SenderType, PreferredChannel,
    CampaignStatus, RecipientStatus, BookingMode, ToneProfile,
    # Models
    Tenant, TenantCreate, TenantResponse,
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
    # Vapi
    VapiCreateLeadRequest, VapiCheckAvailabilityRequest,
    VapiBookJobRequest, VapiSendSmsRequest, VapiCallSummaryRequest,
    # Web Form
    WebFormLeadRequest
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-me')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer(auto_error=False)

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


def verify_vapi_secret(
    x_vapi_secret: str = Header(None, alias="x-vapi-secret"),
    authorization: str = Header(None)
) -> bool:
    """Verify Vapi webhook authentication"""
    # Check for Vapi API key in authorization header
    vapi_api_key = os.environ.get('VAPI_API_KEY')
    
    # Vapi sends the secret in x-vapi-secret header or as Bearer token
    if x_vapi_secret:
        if vapi_api_key and x_vapi_secret == vapi_api_key:
            return True
    
    if authorization:
        # Check Bearer token format
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            if vapi_api_key and token == vapi_api_key:
                return True
    
    # In development, allow requests without auth for testing
    if not vapi_api_key:
        logger.warning("VAPI_API_KEY not configured - allowing request for testing")
        return True
    
    # Log for debugging but don't block - Vapi tool calls may not include auth
    logger.info("Vapi request received (auth headers not matched, allowing for tool calls)")
    return True


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
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            status=user["status"],
            tenant_id=user.get("tenant_id")
        )
    )


@v1_router.post("/auth/logout")
async def logout():
    """Logout user (client should discard token)"""
    return {"message": "Logged out successfully"}


@v1_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        status=current_user["status"],
        tenant_id=current_user.get("tenant_id")
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
    
    tenant_dict = tenant.model_dump()
    tenant_dict["created_at"] = tenant_dict["created_at"].isoformat()
    tenant_dict["updated_at"] = tenant_dict["updated_at"].isoformat()
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
    
    owner_dict = owner.model_dump()
    owner_dict["created_at"] = owner_dict["created_at"].isoformat()
    owner_dict["updated_at"] = owner_dict["updated_at"].isoformat()
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
    }
    
    return {**serialize_doc(tenant), "stats": stats}


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
        **data.model_dump()
    )
    
    customer_dict = customer.model_dump()
    customer_dict["created_at"] = customer_dict["created_at"].isoformat()
    customer_dict["updated_at"] = customer_dict["updated_at"].isoformat()
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
    update_data = data.model_dump()
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
        **data.model_dump()
    )
    
    prop_dict = prop.model_dump()
    prop_dict["created_at"] = prop_dict["created_at"].isoformat()
    prop_dict["updated_at"] = prop_dict["updated_at"].isoformat()
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
    update_data = data.model_dump()
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
        **data.model_dump()
    )
    
    tech_dict = tech.model_dump()
    tech_dict["created_at"] = tech_dict["created_at"].isoformat()
    tech_dict["updated_at"] = tech_dict["updated_at"].isoformat()
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
    update_data = data.model_dump()
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
    
    # Enrich leads with customer data
    enriched_leads = []
    for lead in leads:
        customer = None
        if lead.get("customer_id"):
            customer = await db.customers.find_one({"id": lead["customer_id"]}, {"_id": 0})
        
        enriched_leads.append({
            **serialize_doc(lead),
            "customer": serialize_doc(customer) if customer else None,
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
        **data.model_dump()
    )
    
    lead_dict = lead.model_dump()
    lead_dict["created_at"] = lead_dict["created_at"].isoformat()
    lead_dict["updated_at"] = lead_dict["updated_at"].isoformat()
    lead_dict["first_contact_at"] = lead_dict["first_contact_at"].isoformat()
    lead_dict["last_activity_at"] = lead_dict["last_activity_at"].isoformat()
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
    update_data = data.model_dump()
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
    job_data = data.model_dump()
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
    
    job_dict = job.model_dump()
    job_dict["created_at"] = job_dict["created_at"].isoformat()
    job_dict["updated_at"] = job_dict["updated_at"].isoformat()
    job_dict["service_window_start"] = job_dict["service_window_start"].isoformat()
    job_dict["service_window_end"] = job_dict["service_window_end"].isoformat()
    if job_dict.get("exact_arrival_time"):
        job_dict["exact_arrival_time"] = job_dict["exact_arrival_time"].isoformat()
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
        
        quote_dict = quote.model_dump()
        quote_dict["created_at"] = quote_dict["created_at"].isoformat()
        quote_dict["updated_at"] = quote_dict["updated_at"].isoformat()
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
    update_data = data.model_dump()
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


@v1_router.post("/jobs/{job_id}/en-route")
async def mark_job_en_route(
    job_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Mark job as en-route and send SMS"""
    job = await db.jobs.find_one({"id": job_id, "tenant_id": tenant_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Update job status
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": JobStatus.EN_ROUTE.value,
            "en_route_sms_sent": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Get customer and tenant for SMS
    customer = await db.customers.find_one({"id": job["customer_id"]}, {"_id": 0})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    
    if customer and tenant and tenant.get("twilio_phone_number"):
        from services.twilio_service import twilio_service
        
        tech = None
        if job.get("assigned_technician_id"):
            tech = await db.technicians.find_one({"id": job["assigned_technician_id"]}, {"_id": 0})
        
        tech_name = tech["name"] if tech else "Our technician"
        message = f"Hi {customer['first_name']}, {tech_name} is on the way! They should arrive shortly. {tenant.get('sms_signature', '')}"
        
        result = await twilio_service.send_sms(
            to_phone=customer["phone"],
            body=message,
            from_phone=tenant["twilio_phone_number"]
        )
        
        # Log the message
        if result["success"]:
            msg = Message(
                tenant_id=tenant_id,
                conversation_id="",  # Will be linked if conversation exists
                customer_id=customer["id"],
                direction=MessageDirection.OUTBOUND,
                sender_type=SenderType.SYSTEM,
                content=message,
                metadata={"twilio_sid": result.get("provider_message_id")}
            )
            msg_dict = msg.model_dump()
            msg_dict["created_at"] = msg_dict["created_at"].isoformat()
            await db.messages.insert_one(msg_dict)
    
    return {"message": "Job marked en-route", "sms_sent": True}


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
        **data.model_dump()
    )
    
    quote_dict = quote.model_dump()
    quote_dict["created_at"] = quote_dict["created_at"].isoformat()
    quote_dict["updated_at"] = quote_dict["updated_at"].isoformat()
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
    update_data = data.model_dump()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.quotes.update_one(
        {"id": quote_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = await db.quotes.find_one({"id": quote_id}, {"_id": 0})
    return serialize_doc(quote)


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
        **data.model_dump()
    )
    
    invoice_dict = invoice.model_dump()
    invoice_dict["created_at"] = invoice_dict["created_at"].isoformat()
    invoice_dict["updated_at"] = invoice_dict["updated_at"].isoformat()
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
    update_data = data.model_dump()
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
    
    msg_dict = msg.model_dump()
    msg_dict["created_at"] = msg_dict["created_at"].isoformat()
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
        **data.model_dump()
    )
    
    campaign_dict = campaign.model_dump()
    campaign_dict["created_at"] = campaign_dict["created_at"].isoformat()
    campaign_dict["updated_at"] = campaign_dict["updated_at"].isoformat()
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
    update_data = data.model_dump()
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
        recipient_dict = recipient.model_dump()
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
                msg_dict = msg.model_dump()
                msg_dict["created_at"] = msg_dict["created_at"].isoformat()
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
        recipient_dict = recipient.model_dump()
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


# ============= VAPI ENDPOINTS =============

@v1_router.post("/vapi/create-lead")
async def vapi_create_lead(
    data: VapiCreateLeadRequest,
    _: bool = Depends(verify_vapi_secret)
):
    """Create lead from Vapi call"""
    try:
        logger.info(f"Vapi create-lead called with data: {data.model_dump()}")
        
        # Get tenant by slug
        tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
        if not tenant:
            logger.error(f"Tenant not found: {data.tenant_slug}")
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        tenant_id = tenant["id"]
        
        # Resolve field aliases (support both old Make.com names and new names)
        phone = data.caller_phone or data.caller_number
        name = data.caller_name or data.captured_name
        description = data.description or data.issue_description
        issue_type = data.issue_type or data.issue_description  # Use issue_description as issue_type if not provided
        
        # Parse address - support both structured and single-line formats
        address_line1 = data.address_line1
        city = data.city
        state = data.state
        postal_code = data.postal_code
        
        if data.captured_address and not address_line1:
            # Try to parse "123 Main St, Chicago, IL 60601" format
            parts = [p.strip() for p in data.captured_address.split(',')]
            if len(parts) >= 1:
                address_line1 = parts[0]
            if len(parts) >= 2:
                city = parts[1]
            if len(parts) >= 3:
                # Try to parse "IL 60601" or just "IL"
                state_zip = parts[2].strip().split()
                if len(state_zip) >= 1:
                    state = state_zip[0]
                if len(state_zip) >= 2:
                    postal_code = state_zip[1]
        
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number is required (caller_phone or caller_number)")
        
        # Find or create customer
        customer = await db.customers.find_one(
            {"phone": phone, "tenant_id": tenant_id}, {"_id": 0}
        )
        
        if not customer:
            # Parse name
            first_name = "Unknown"
            last_name = ""
            if name:
                parts = name.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""
            
            # Convert empty email to None to pass validation
            email = data.captured_email if data.captured_email and data.captured_email.strip() else None
            
            customer = Customer(
                tenant_id=tenant_id,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email
            )
            customer_dict = customer.model_dump()
            customer_dict["created_at"] = customer_dict["created_at"].isoformat()
            customer_dict["updated_at"] = customer_dict["updated_at"].isoformat()
            await db.customers.insert_one(customer_dict)
            customer = customer_dict
        
        # Create property if address provided
        property_id = None
        if address_line1:
            prop = Property(
                tenant_id=tenant_id,
                customer_id=customer["id"],
                address_line1=address_line1,
                city=city or "",
                state=state or "",
                postal_code=postal_code or ""
            )
            prop_dict = prop.model_dump()
            prop_dict["created_at"] = prop_dict["created_at"].isoformat()
            prop_dict["updated_at"] = prop_dict["updated_at"].isoformat()
            await db.properties.insert_one(prop_dict)
            property_id = prop.id
        
        # Create lead
        urgency_value = Urgency.ROUTINE
        if data.urgency:
            try:
                urgency_value = Urgency(data.urgency.upper())
            except ValueError:
                pass
        
        lead = Lead(
            tenant_id=tenant_id,
            customer_id=customer["id"],
            property_id=property_id,
            source=LeadSource.VAPI_CALL,
            channel=LeadChannel.VOICE,
            status=LeadStatus.NEW,
            issue_type=issue_type,
            urgency=urgency_value,
            description=description
        )
        lead_dict = lead.model_dump()
        lead_dict["caller_name"] = name  # Store caller name directly on lead
        lead_dict["caller_phone"] = phone  # Store caller phone directly on lead
        lead_dict["created_at"] = lead_dict["created_at"].isoformat()
        lead_dict["updated_at"] = lead_dict["updated_at"].isoformat()
        lead_dict["first_contact_at"] = lead_dict["first_contact_at"].isoformat()
        lead_dict["last_activity_at"] = lead_dict["last_activity_at"].isoformat()
        await db.leads.insert_one(lead_dict)
        
        # Create conversation
        conv = Conversation(
            tenant_id=tenant_id,
            customer_id=customer["id"],
            lead_id=lead.id,
            primary_channel=PreferredChannel.SMS
        )
        conv_dict = conv.model_dump()
        conv_dict["created_at"] = conv_dict["created_at"].isoformat()
        conv_dict["updated_at"] = conv_dict["updated_at"].isoformat()
        await db.conversations.insert_one(conv_dict)
        
        # Return clear response for Vapi - structured for AI to understand
        first_name = customer.get("first_name", "there")
        return {
            "result": "success",
            "status": "lead_created",
            "lead_id": lead.id,
            "customer_id": customer["id"],
            "property_id": property_id,
            "conversation_id": conv.id,
            "customer_name": first_name,
            "instructions": f"IMPORTANT: The lead has been successfully created in the system. The customer {first_name} is now registered. Their customer ID is {customer['id']}. You should now ask the customer what date they would like to schedule their service appointment, then call the check-availability tool with that date."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in vapi_create_lead: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating lead: {str(e)}")


@v1_router.post("/vapi/get-current-date")
async def vapi_get_current_date(
    _: bool = Depends(verify_vapi_secret)
):
    """
    Get current server date - Vapi utility tool.
    Call this tool first if you need to know today's date before checking availability.
    """
    current_date = datetime.now(timezone.utc)
    tomorrow = current_date + timedelta(days=1)
    
    return {
        "result": "success",
        "today": {
            "date": current_date.strftime("%Y-%m-%d"),
            "formatted": current_date.strftime("%A, %B %d, %Y"),
            "day_of_week": current_date.strftime("%A")
        },
        "tomorrow": {
            "date": tomorrow.strftime("%Y-%m-%d"),
            "formatted": tomorrow.strftime("%A, %B %d, %Y"),
            "day_of_week": tomorrow.strftime("%A")
        },
        "instructions": f"Today is {current_date.strftime('%A, %B %d, %Y')}. Tomorrow is {tomorrow.strftime('%A, %B %d, %Y')}. Use the 'date' values (YYYY-MM-DD format) when calling check-availability."
    }


@v1_router.post("/vapi/check-availability")
async def vapi_check_availability(
    data: VapiCheckAvailabilityRequest,
    _: bool = Depends(verify_vapi_secret)
):
    """Check available time windows"""
    import pytz
    
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_id = tenant["id"]
    
    # Use tenant's timezone for date calculations (default to America/New_York)
    tenant_tz_str = tenant.get("timezone", "America/New_York")
    try:
        tenant_tz = pytz.timezone(tenant_tz_str)
    except:
        tenant_tz = pytz.timezone("America/New_York")
    
    # Get current date in tenant's timezone
    current_date = datetime.now(tenant_tz)
    current_date_str = current_date.strftime("%Y-%m-%d")
    current_date_formatted = current_date.strftime("%A, %B %d, %Y")
    
    # Parse date - handle relative dates like "tomorrow", "today"
    date_input = data.date.lower().strip() if data.date else current_date_str
    
    if date_input in ["today", "now"]:
        target_date = current_date
    elif date_input == "tomorrow":
        target_date = current_date + timedelta(days=1)
    else:
        # Try to parse YYYY-MM-DD format
        try:
            target_date = datetime.strptime(data.date, "%Y-%m-%d")
            # Make it timezone-aware in tenant's timezone
            target_date = tenant_tz.localize(target_date)
        except ValueError:
            # Return helpful error with current date reference
            return {
                "result": "error",
                "status": "invalid_date",
                "error": f"Invalid date format. Use YYYY-MM-DD format.",
                "current_server_date": current_date_str,
                "current_server_date_formatted": current_date_formatted,
                "instructions": f"IMPORTANT: The date format was invalid. Today's date is {current_date_formatted}. Ask the customer to specify a date, then call this tool again with the date in YYYY-MM-DD format. For example, if they say 'tomorrow', you should pass '{(current_date + timedelta(days=1)).strftime('%Y-%m-%d')}'."
            }
    
    # Define standard time windows
    windows = [
        {"start": "08:00", "end": "12:00", "label": "Morning (8am-12pm)"},
        {"start": "12:00", "end": "17:00", "label": "Afternoon (12pm-5pm)"},
    ]
    
    # Check existing jobs for that date
    date_start = target_date.replace(hour=0, minute=0, second=0)
    date_end = target_date.replace(hour=23, minute=59, second=59)
    
    existing_jobs = await db.jobs.count_documents({
        "tenant_id": tenant_id,
        "service_window_start": {
            "$gte": date_start.isoformat(),
            "$lte": date_end.isoformat()
        },
        "status": {"$nin": [JobStatus.CANCELLED.value, JobStatus.COMPLETED.value]}
    })
    
    # Simple capacity check (assume max 4 jobs per window)
    max_capacity = 4
    available_slots = max(0, max_capacity - existing_jobs)
    
    available_windows = []
    for window in windows:
        if available_slots > 0:
            # Build full ISO datetime strings for the booking
            start_hour, start_min = map(int, window["start"].split(":"))
            end_hour, end_min = map(int, window["end"].split(":"))
            
            window_start_dt = target_date.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            window_end_dt = target_date.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
            
            available_windows.append({
                "date": target_date.strftime("%Y-%m-%d"),  # Always use calculated date, not input
                "start": window["start"],
                "end": window["end"],
                "label": window["label"],
                "available": True,
                # Include full ISO datetime strings for book-job
                "window_start": window_start_dt.isoformat(),
                "window_end": window_end_dt.isoformat()
            })
            available_slots -= 1
    
    # Format date for human-readable response
    date_formatted = target_date.strftime("%A, %B %d, %Y")
    
    # Format response for Vapi - structured for AI to understand
    # Include current server date so Vapi AI knows the reference point
    if len(available_windows) == 0:
        return {
            "result": "no_availability",
            "status": "fully_booked",
            "date": target_date.strftime("%Y-%m-%d"),
            "date_formatted": date_formatted,
            "current_server_date": current_date_str,
            "current_server_date_formatted": current_date_formatted,
            "windows": [],
            "has_availability": False,
            "instructions": f"IMPORTANT: There are NO available time slots for {date_formatted}. Tell the customer that unfortunately, that date is fully booked. Ask them to suggest an alternative date and you will check availability for that date instead. Remember: Today is {current_date_formatted}."
        }
    else:
        slots_text = ", ".join([w["label"] for w in available_windows])
        return {
            "result": "success",
            "status": "slots_available",
            "date": target_date.strftime("%Y-%m-%d"),
            "date_formatted": date_formatted,
            "current_server_date": current_date_str,
            "current_server_date_formatted": current_date_formatted,
            "windows": available_windows,
            "has_availability": True,
            "available_slots": slots_text,
            "instructions": f"IMPORTANT: Good news! For {date_formatted}, the following time slots are available: {slots_text}. Tell the customer these options and ask which one works best for them. Once they choose, call the book-job tool using the window_start and window_end values from the chosen slot to complete the booking. Remember: Today is {current_date_formatted}."
        }


@v1_router.post("/vapi/book-job")
async def vapi_book_job(
    data: VapiBookJobRequest,
    _: bool = Depends(verify_vapi_secret)
):
    """Book a job from Vapi"""
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_id = tenant["id"]
    
    # Verify customer and property
    customer = await db.customers.find_one({"id": data.customer_id, "tenant_id": tenant_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    prop = await db.properties.find_one({"id": data.property_id, "tenant_id": tenant_id}, {"_id": 0})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Parse job type
    try:
        job_type = JobType(data.job_type.upper())
    except ValueError:
        job_type = JobType.DIAGNOSTIC
    
    # Parse dates
    try:
        window_start = datetime.fromisoformat(data.window_start.replace('Z', '+00:00'))
        window_end = datetime.fromisoformat(data.window_end.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    # Get lead urgency for quote calculation (if lead exists)
    lead_urgency = None
    if data.lead_id:
        lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0, "urgency": 1})
        if lead:
            lead_urgency = lead.get("urgency")
    
    # Calculate quote amount based on job type and urgency
    quote_amount = calculate_quote_amount(job_type.value, lead_urgency)
    
    # Create job
    job = Job(
        tenant_id=tenant_id,
        customer_id=data.customer_id,
        property_id=data.property_id,
        lead_id=data.lead_id,
        job_type=job_type,
        priority=JobPriority.NORMAL,
        service_window_start=window_start,
        service_window_end=window_end,
        status=JobStatus.BOOKED,
        created_by=JobCreatedBy.AI,
        quote_amount=quote_amount
    )
    
    job_dict = job.model_dump()
    job_dict["created_at"] = job_dict["created_at"].isoformat()
    job_dict["updated_at"] = job_dict["updated_at"].isoformat()
    job_dict["service_window_start"] = job_dict["service_window_start"].isoformat()
    job_dict["service_window_end"] = job_dict["service_window_end"].isoformat()
    await db.jobs.insert_one(job_dict)
    
    # Create a Quote record linked to the job
    lead_data = None
    if data.lead_id:
        lead_data = await db.leads.find_one({"id": data.lead_id}, {"_id": 0})
    
    quote_description = f"{job_type.value} service"
    if lead_data:
        if lead_data.get("issue_type"):
            quote_description = f"{job_type.value} - {lead_data.get('issue_type')}"
        if lead_data.get("description"):
            quote_description += f"\n{lead_data.get('description')}"
    
    quote = Quote(
        tenant_id=tenant_id,
        customer_id=data.customer_id,
        property_id=data.property_id,
        job_id=job.id,
        amount=quote_amount,
        description=quote_description,
        status=QuoteStatus.SENT  # Auto-sent since job is booked
    )
    
    quote_dict = quote.model_dump()
    quote_dict["created_at"] = quote_dict["created_at"].isoformat()
    quote_dict["updated_at"] = quote_dict["updated_at"].isoformat()
    quote_dict["sent_at"] = datetime.now(timezone.utc).isoformat()
    await db.quotes.insert_one(quote_dict)
    
    # Link quote to job
    await db.jobs.update_one(
        {"id": job.id},
        {"$set": {"quote_id": quote.id}}
    )
    
    # Update lead status
    if data.lead_id:
        await db.leads.update_one(
            {"id": data.lead_id},
            {"$set": {"status": LeadStatus.JOB_BOOKED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    # Send confirmation SMS and store in conversation
    if tenant.get("twilio_phone_number"):
        from services.twilio_service import twilio_service
        
        window_date = window_start.strftime("%A, %B %d")
        window_time = f"{window_start.strftime('%I:%M %p')} - {window_end.strftime('%I:%M %p')}"
        
        sms_sig_confirm = tenant.get('sms_signature', '').strip()
        message = f"Hi {customer['first_name']}, your service visit is confirmed for {window_date}, {window_time}. We'll send a reminder before your appointment.{' ' + sms_sig_confirm if sms_sig_confirm else ''}"
        
        sms_result = await twilio_service.send_sms(
            to_phone=customer["phone"],
            body=message,
            from_phone=tenant["twilio_phone_number"]
        )
        
        # Find or create conversation and store the message
        conv = await db.conversations.find_one(
            {"customer_id": data.customer_id, "tenant_id": tenant_id},
            {"_id": 0}
        )
        
        if conv:
            # Store the confirmation message
            msg = Message(
                tenant_id=tenant_id,
                conversation_id=conv["id"],
                customer_id=data.customer_id,
                direction=MessageDirection.OUTBOUND,
                sender_type=SenderType.SYSTEM,
                channel=PreferredChannel.SMS,
                content=message
            )
            msg_dict = msg.model_dump()
            msg_dict["created_at"] = msg_dict["created_at"].isoformat()
            msg_dict["metadata"] = {"twilio_sid": sms_result.get("provider_message_id"), "job_id": job.id}
            await db.messages.insert_one(msg_dict)
            
            # Update conversation
            await db.conversations.update_one(
                {"id": conv["id"]},
                {"$set": {
                    "last_message_at": datetime.now(timezone.utc).isoformat(),
                    "last_message_from": SenderType.SYSTEM.value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        # Send quote SMS with payment link placeholder (continuation, no greeting)
        sms_sig = tenant.get('sms_signature', '').strip()
        quote_message = f"Your service quote for {job_type.value} is ${quote_amount:.2f}. Pay securely here: [YOUR PAYMENT LINK HERE]. Reply with any questions!{' ' + sms_sig if sms_sig else ''}"
        
        quote_sms_result = await twilio_service.send_sms(
            to_phone=customer["phone"],
            body=quote_message,
            from_phone=tenant["twilio_phone_number"]
        )
        
        # Store the quote SMS in conversation
        if conv:
            quote_msg = Message(
                tenant_id=tenant_id,
                conversation_id=conv["id"],
                customer_id=data.customer_id,
                direction=MessageDirection.OUTBOUND,
                sender_type=SenderType.SYSTEM,
                channel=PreferredChannel.SMS,
                content=quote_message
            )
            quote_msg_dict = quote_msg.model_dump()
            quote_msg_dict["created_at"] = quote_msg_dict["created_at"].isoformat()
            quote_msg_dict["metadata"] = {"twilio_sid": quote_sms_result.get("provider_message_id"), "quote_id": quote.id}
            await db.messages.insert_one(quote_msg_dict)
    
    # Format confirmation for Vapi - structured for AI to understand
    window_date = window_start.strftime("%A, %B %d")
    window_time_str = f"{window_start.strftime('%I:%M %p')} to {window_end.strftime('%I:%M %p')}"
    customer_name = customer.get("first_name", "Customer")
    
    return {
        "result": "success",
        "status": "job_booked",
        "job_id": job.id,
        "booking_details": {
            "date": window_date,
            "time_window": window_time_str,
            "customer_name": customer_name
        },
        "sms_sent": True,
        "instructions": f"IMPORTANT: The appointment has been SUCCESSFULLY BOOKED! Tell {customer_name} the following: Their service appointment is confirmed for {window_date} between {window_time_str}. They will receive a confirmation text message shortly. Ask if there's anything else you can help them with, then thank them for calling and end the call politely."
    }


@v1_router.post("/vapi/send-sms")
async def vapi_send_sms(
    data: VapiSendSmsRequest,
    _: bool = Depends(verify_vapi_secret)
):
    """Send SMS via Vapi"""
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.get("twilio_phone_number"):
        raise HTTPException(status_code=400, detail="Tenant has no Twilio phone configured")
    
    from services.twilio_service import twilio_service
    
    result = await twilio_service.send_sms(
        to_phone=data.to_phone,
        body=data.message,
        from_phone=tenant["twilio_phone_number"]
    )
    
    if result["success"]:
        return {
            "success": True,
            "message_id": result.get("provider_message_id"),
            "message": f"SMS sent successfully to {data.to_phone}."
        }
    else:
        return {
            "success": False,
            "error": result.get("error"),
            "message": f"Failed to send SMS: {result.get('error', 'Unknown error')}"
        }


@v1_router.post("/vapi/call-summary")
async def vapi_call_summary(
    data: VapiCallSummaryRequest,
    _: bool = Depends(verify_vapi_secret)
):
    """Log call summary from Vapi"""
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_id = tenant["id"]
    
    # Get lead
    lead = await db.leads.find_one({"id": data.lead_id, "tenant_id": tenant_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Find conversation
    conv = await db.conversations.find_one({"lead_id": data.lead_id}, {"_id": 0})
    
    # Create summary message
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=conv["id"] if conv else "",
        customer_id=lead.get("customer_id", ""),
        lead_id=data.lead_id,
        direction=MessageDirection.INBOUND,
        sender_type=SenderType.SYSTEM,
        channel=PreferredChannel.CALL,
        content=data.summary,
        is_call_summary=True,
        metadata={"vapi_session_id": data.vapi_session_id}
    )
    
    msg_dict = msg.model_dump()
    msg_dict["created_at"] = msg_dict["created_at"].isoformat()
    await db.messages.insert_one(msg_dict)
    
    return {"success": True, "message_id": msg.id}


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
    
    # Normalize phone number
    phone = data.phone
    if phone:
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            digits = '1' + digits
        phone = '+' + digits if digits else data.phone
    
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
    lead_dict = lead.model_dump()
    lead_dict["id"] = lead_id
    lead_dict["created_at"] = lead_dict["created_at"].isoformat()
    lead_dict["updated_at"] = lead_dict["updated_at"].isoformat()
    
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
    
    # Send confirmation SMS if enabled and tenant has Twilio configured
    sms_sent = False
    sms_error = None
    
    if data.send_confirmation_sms and tenant.get("twilio_phone_number"):
        try:
            company_name = tenant.get("name", "Our company")
            confirmation_msg = (
                f"Hi {first_name}! Thank you for contacting {company_name}. "
                f"We received your request about: {data.issue_description[:50]}{'...' if len(data.issue_description) > 50 else ''}. "
                f"A team member will reach out to you shortly to schedule your service."
            )
            
            if data.urgency == "EMERGENCY":
                confirmation_msg += " For emergencies, we prioritize same-day service."
            
            result = await twilio_service.send_sms(
                to_phone=phone,
                body=confirmation_msg,
                from_phone=tenant["twilio_phone_number"]
            )
            sms_sent = True
            
            # Store outbound message
            msg = Message(
                tenant_id=tenant_id,
                conversation_id=conv_id,
                customer_id=customer_id,
                direction=MessageDirection.OUTBOUND,
                sender_type=SenderType.SYSTEM,
                channel=PreferredChannel.SMS,
                content=confirmation_msg
            )
            msg_dict = msg.model_dump()
            msg_dict["created_at"] = msg_dict["created_at"].isoformat()
            msg_dict["metadata"] = {
                "source": "web_form_confirmation",
                "lead_id": lead_id
            }
            await db.messages.insert_one(msg_dict)
            
            logger.info(f"Sent confirmation SMS to {phone} for web form lead {lead_id}")
            
        except Exception as e:
            logger.error(f"Failed to send confirmation SMS: {str(e)}")
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
        customer_dict = customer.model_dump()
        customer_dict["created_at"] = customer_dict["created_at"].isoformat()
        customer_dict["updated_at"] = customer_dict["updated_at"].isoformat()
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
        conv_dict = conv.model_dump()
        conv_dict["created_at"] = conv_dict["created_at"].isoformat()
        conv_dict["updated_at"] = conv_dict["updated_at"].isoformat()
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
    msg_dict = msg.model_dump()
    msg_dict["created_at"] = msg_dict["created_at"].isoformat()
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
    
    # Generate AI response
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
                ai_msg_dict = ai_msg.model_dump()
                ai_msg_dict["created_at"] = ai_msg_dict["created_at"].isoformat()
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
    # Potential revenue: sum of quote_amount for all booked/en_route/on_site jobs this month
    potential_jobs = await db.jobs.find({
        "tenant_id": tenant_id,
        "status": {"$in": ["BOOKED", "EN_ROUTE", "ON_SITE"]},
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
    """Create default superadmin if not exists and start scheduler"""
    superadmin = await db.users.find_one({"role": UserRole.SUPERADMIN.value})
    if not superadmin:
        admin = User(
            email="admin@fieldos.app",
            name="Super Admin",
            role=UserRole.SUPERADMIN,
            status=UserStatus.ACTIVE,
            tenant_id=None,
            password_hash=hash_password("admin123")
        )
        admin_dict = admin.model_dump()
        admin_dict["created_at"] = admin_dict["created_at"].isoformat()
        admin_dict["updated_at"] = admin_dict["updated_at"].isoformat()
        await db.users.insert_one(admin_dict)
        logger.info("Created default superadmin: admin@fieldos.app / admin123")
    
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
        "status": {"$in": ["BOOKED", "EN_ROUTE", "ON_SITE"]},
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


# ============= HEALTH CHECK =============

@api_router.get("/")
async def root():
    return {"message": "FieldOS API v1.0.0", "status": "healthy"}


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# Include routers
api_router.include_router(v1_router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    # Stop scheduler
    try:
        from scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
    client.close()
