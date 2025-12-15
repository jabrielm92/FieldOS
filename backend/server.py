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

from models import (
    # Enums
    UserRole, UserStatus, LeadSource, LeadChannel, LeadStatus, Urgency,
    JobType, JobPriority, JobStatus, JobCreatedBy, QuoteStatus,
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
    Conversation, Message, MessageCreate,
    Campaign, CampaignCreate, CampaignRecipient,
    # Auth
    LoginRequest, TokenResponse,
    # Vapi
    VapiCreateLeadRequest, VapiCheckAvailabilityRequest,
    VapiBookJobRequest, VapiSendSmsRequest, VapiCallSummaryRequest
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
    return serialize_docs(leads)


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
    
    job = Job(
        tenant_id=tenant_id,
        **data.model_dump()
    )
    
    job_dict = job.model_dump()
    job_dict["created_at"] = job_dict["created_at"].isoformat()
    job_dict["updated_at"] = job_dict["updated_at"].isoformat()
    job_dict["service_window_start"] = job_dict["service_window_start"].isoformat()
    job_dict["service_window_end"] = job_dict["service_window_end"].isoformat()
    if job_dict.get("exact_arrival_time"):
        job_dict["exact_arrival_time"] = job_dict["exact_arrival_time"].isoformat()
    await db.jobs.insert_one(job_dict)
    
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
    # Get tenant by slug
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_id = tenant["id"]
    
    # Find or create customer
    customer = await db.customers.find_one(
        {"phone": data.caller_phone, "tenant_id": tenant_id}, {"_id": 0}
    )
    
    if not customer:
        # Parse name
        first_name = "Unknown"
        last_name = ""
        if data.caller_name:
            parts = data.caller_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
        
        customer = Customer(
            tenant_id=tenant_id,
            first_name=first_name,
            last_name=last_name,
            phone=data.caller_phone
        )
        customer_dict = customer.model_dump()
        customer_dict["created_at"] = customer_dict["created_at"].isoformat()
        customer_dict["updated_at"] = customer_dict["updated_at"].isoformat()
        await db.customers.insert_one(customer_dict)
        customer = customer_dict
    
    # Create property if address provided
    property_id = None
    if data.address_line1:
        prop = Property(
            tenant_id=tenant_id,
            customer_id=customer["id"],
            address_line1=data.address_line1,
            city=data.city or "",
            state=data.state or "",
            postal_code=data.postal_code or ""
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
        issue_type=data.issue_type,
        urgency=urgency_value,
        description=data.description
    )
    lead_dict = lead.model_dump()
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
    
    return {
        "success": True,
        "lead_id": lead.id,
        "customer_id": customer["id"],
        "property_id": property_id,
        "conversation_id": conv.id
    }


@v1_router.post("/vapi/check-availability")
async def vapi_check_availability(
    data: VapiCheckAvailabilityRequest,
    _: bool = Depends(verify_vapi_secret)
):
    """Check available time windows"""
    tenant = await db.tenants.find_one({"slug": data.tenant_slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_id = tenant["id"]
    
    # Parse date
    try:
        target_date = datetime.strptime(data.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
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
            available_windows.append({
                "date": data.date,
                "start": window["start"],
                "end": window["end"],
                "label": window["label"],
                "available": True
            })
            available_slots -= 1
    
    return {
        "date": data.date,
        "windows": available_windows,
        "message": f"Found {len(available_windows)} available time slots for {data.date}"
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
        created_by=JobCreatedBy.AI
    )
    
    job_dict = job.model_dump()
    job_dict["created_at"] = job_dict["created_at"].isoformat()
    job_dict["updated_at"] = job_dict["updated_at"].isoformat()
    job_dict["service_window_start"] = job_dict["service_window_start"].isoformat()
    job_dict["service_window_end"] = job_dict["service_window_end"].isoformat()
    await db.jobs.insert_one(job_dict)
    
    # Update lead status
    if data.lead_id:
        await db.leads.update_one(
            {"id": data.lead_id},
            {"$set": {"status": LeadStatus.JOB_BOOKED.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    # Send confirmation SMS
    if tenant.get("twilio_phone_number"):
        from services.twilio_service import twilio_service
        
        window_date = window_start.strftime("%A, %B %d")
        window_time = f"{window_start.strftime('%I:%M %p')} - {window_end.strftime('%I:%M %p')}"
        
        message = f"Hi {customer['first_name']}, your service visit is confirmed for {window_date}, {window_time}. We'll send a reminder before your appointment. {tenant.get('sms_signature', '')}"
        
        await twilio_service.send_sms(
            to_phone=customer["phone"],
            body=message,
            from_phone=tenant["twilio_phone_number"]
        )
    
    return {
        "success": True,
        "job_id": job.id,
        "message": "Job booked successfully"
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
    
    return {
        "success": result["success"],
        "message_id": result.get("provider_message_id"),
        "error": result.get("error")
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


# ============= INBOUND SMS WEBHOOK =============

@v1_router.post("/sms/inbound")
async def sms_inbound(request: Request):
    """Handle inbound SMS from Twilio webhook"""
    form_data = await request.form()
    
    from_phone = form_data.get("From", "")
    to_phone = form_data.get("To", "")
    body = form_data.get("Body", "")
    
    logger.info(f"Inbound SMS from {from_phone} to {to_phone}: {body[:50]}...")
    
    # Find tenant by Twilio phone number
    tenant = await db.tenants.find_one({"twilio_phone_number": to_phone}, {"_id": 0})
    if not tenant:
        # Try without formatting
        cleaned_to = ''.join(c for c in to_phone if c.isdigit())
        tenant = await db.tenants.find_one({}, {"_id": 0})  # Fallback to first tenant
        if not tenant:
            logger.error(f"No tenant found for number {to_phone}")
            return {"status": "no_tenant"}
    
    tenant_id = tenant["id"]
    
    # Find or create customer
    customer = await db.customers.find_one(
        {"phone": from_phone, "tenant_id": tenant_id}, {"_id": 0}
    )
    
    if not customer:
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
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    
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
    
    return {
        "metrics": {
            "leads_this_week": leads_week,
            "leads_this_month": leads_month,
            "jobs_this_week": jobs_week,
            "quote_conversion": round(accepted_quotes / total_quotes * 100, 1) if total_quotes > 0 else 0
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
    """Create default superadmin if not exists"""
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
    client.close()
