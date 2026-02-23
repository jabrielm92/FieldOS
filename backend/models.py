"""
FieldOS Data Models - Pydantic models for all entities
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Any
from datetime import datetime, timezone, date
from enum import Enum
import uuid


def generate_id():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


# ============= ENUMS =============

class BookingMode(str, Enum):
    TIME_WINDOWS = "TIME_WINDOWS"
    EXACT_TIMES = "EXACT_TIMES"


class ToneProfile(str, Enum):
    PROFESSIONAL = "PROFESSIONAL"
    FRIENDLY = "FRIENDLY"
    BLUE_COLLAR_DIRECT = "BLUE_COLLAR_DIRECT"


class UserRole(str, Enum):
    SUPERADMIN = "SUPERADMIN"
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    DISPATCH = "DISPATCH"
    TECH = "TECH"
    VIEWONLY = "VIEWONLY"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class PreferredChannel(str, Enum):
    SMS = "SMS"
    CALL = "CALL"
    EMAIL = "EMAIL"


class PropertyType(str, Enum):
    RESIDENTIAL = "RESIDENTIAL"
    COMMERCIAL = "COMMERCIAL"


class LeadSource(str, Enum):
    VAPI_CALL = "VAPI_CALL"
    MISSED_CALL_SMS = "MISSED_CALL_SMS"
    WEB_FORM = "WEB_FORM"
    LANDING_PAGE = "LANDING_PAGE"
    FB_LEAD = "FB_LEAD"
    MANUAL = "MANUAL"
    PORTAL_REQUEST = "PORTAL_REQUEST"
    SELF_HOSTED_VOICE = "SELF_HOSTED_VOICE"


class LeadChannel(str, Enum):
    VOICE = "VOICE"
    SMS = "SMS"
    FORM = "FORM"
    EMAIL = "EMAIL"


class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    JOB_BOOKED = "JOB_BOOKED"
    NO_RESPONSE = "NO_RESPONSE"
    LOST = "LOST"


class Urgency(str, Enum):
    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"


class JobType(str, Enum):
    DIAGNOSTIC = "DIAGNOSTIC"
    REPAIR = "REPAIR"
    INSTALL = "INSTALL"
    MAINTENANCE = "MAINTENANCE"
    INSPECTION = "INSPECTION"


class JobPriority(str, Enum):
    EMERGENCY = "EMERGENCY"
    HIGH = "HIGH"
    NORMAL = "NORMAL"


class JobStatus(str, Enum):
    BOOKED = "BOOKED"
    EN_ROUTE = "EN_ROUTE"
    ON_SITE = "ON_SITE"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"


class JobCreatedBy(str, Enum):
    AI = "AI"
    STAFF = "STAFF"
    CUSTOMER_SELF = "CUSTOMER_SELF"


class QuoteStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    LOST = "LOST"


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


class ConversationStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class MessageDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class SenderType(str, Enum):
    CUSTOMER = "CUSTOMER"
    AI = "AI"
    STAFF = "STAFF"
    SYSTEM = "SYSTEM"


class CampaignType(str, Enum):
    REACTIVATION = "REACTIVATION"
    TUNEUP = "TUNEUP"
    SPECIAL_OFFER = "SPECIAL_OFFER"


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class RecipientStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    RESPONDED = "RESPONDED"
    OPTED_OUT = "OPTED_OUT"


# ============= MODELS =============

class TenantBase(BaseModel):
    name: str
    slug: str
    subdomain: Optional[str] = None
    timezone: str = "America/New_York"
    service_area: Optional[str] = None
    primary_contact_name: str
    primary_contact_email: EmailStr
    primary_phone: str
    booking_mode: BookingMode = BookingMode.TIME_WINDOWS
    emergency_rules: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    twilio_messaging_service_sid: Optional[str] = None
    tone_profile: ToneProfile = ToneProfile.PROFESSIONAL
    sms_signature: Optional[str] = None
    
    # White-Label Branding
    branding: Optional[dict] = None  # Contains BrandingSettings as dict
    
    # Voice AI Configuration
    voice_ai_enabled: bool = False
    
    # Twilio Voice Credentials (per-tenant)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_api_key_sid: Optional[str] = None
    twilio_api_key_secret: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    twilio_messaging_service_sid: Optional[str] = None
    
    # OpenAI Configuration (per-tenant)
    openai_api_key: Optional[str] = None
    
    # ElevenLabs Configuration (per-tenant) 
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    
    # Voice AI Settings
    voice_provider: str = "elevenlabs"  # elevenlabs, twilio
    voice_model: str = "eleven_turbo_v2_5"
    voice_name: Optional[str] = None
    voice_greeting: Optional[str] = None
    voice_system_prompt: Optional[str] = None
    voice_collect_fields: List[str] = ["name", "phone", "address", "issue", "urgency"]
    voice_business_hours: Optional[dict] = None  # {"start": "08:00", "end": "18:00", "days": [0,1,2,3,4]}
    voice_after_hours_message: Optional[str] = None
    
    # Industry Template
    industry_template: str = "hvac"  # hvac, plumbing, electrical, landscaping, cleaning, general
    
    # Automation Settings
    auto_review_request_days: int = 3  # Days after job completion to send review request
    auto_payment_reminder_days: int = 7  # Days after invoice due date to send reminder
    stripe_secret_key: Optional[str] = None


# ============= BRANDING MODELS =============

class BrandingSettings(BaseModel):
    """White-label branding settings for a tenant"""
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: str = "#0066CC"
    secondary_color: str = "#004499"
    accent_color: str = "#FF6600"
    text_on_primary: str = "#FFFFFF"
    font_family: str = "Inter"
    
    # Email branding
    email_from_name: Optional[str] = None
    email_reply_to: Optional[str] = None
    
    # SMS branding
    sms_sender_name: Optional[str] = None
    
    # Portal branding
    portal_title: Optional[str] = None
    portal_welcome_message: Optional[str] = None
    portal_support_email: Optional[str] = None
    portal_support_phone: Optional[str] = None
    
    # Review URLs
    google_review_url: Optional[str] = None
    yelp_review_url: Optional[str] = None
    facebook_review_url: Optional[str] = None
    
    # Custom domain (placeholder for future)
    custom_domain: Optional[str] = None
    custom_domain_verified: bool = False
    
    # White-label toggle
    white_label_enabled: bool = False


class CustomerPortalToken(BaseModel):
    """Token for customer portal access"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: str
    token: str  # Secure random token
    expires_at: Optional[datetime] = None  # None = never expires
    last_accessed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class ServiceRequest(BaseModel):
    """Customer-initiated service request from portal"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: str
    property_id: Optional[str] = None
    issue_description: str
    urgency: Urgency = Urgency.ROUTINE
    preferred_date: Optional[str] = None
    preferred_time_slot: Optional[str] = None  # morning, afternoon, evening
    status: str = "PENDING"  # PENDING, REVIEWED, CONVERTED_TO_LEAD, CANCELLED
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewSettings(BaseModel):
    """Review request automation settings"""
    enabled: bool = True
    delay_hours: int = 2
    google_review_url: Optional[str] = None
    yelp_review_url: Optional[str] = None
    facebook_review_url: Optional[str] = None
    preferred_platform: str = "GOOGLE"
    message_template: Optional[str] = None


class InvoiceSettings(BaseModel):
    """Invoice configuration settings"""
    default_payment_terms: int = 10  # Days until due
    default_tax_rate: float = 0.0
    invoice_prefix: str = "INV"
    next_invoice_number: int = 1
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_logo_url: Optional[str] = None
    invoice_footer_text: str = "Thank you for your business!"
    payment_instructions: str = "Pay online or call us to pay by phone."
    auto_reminder_enabled: bool = True
    auto_reminder_days: List[int] = [3, 7, 14]


class TenantCreate(TenantBase):
    owner_email: EmailStr
    owner_name: str
    owner_password: str


class Tenant(TenantBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    timezone: str
    primary_contact_name: str
    primary_contact_email: str
    primary_phone: str
    booking_mode: BookingMode
    tone_profile: ToneProfile
    twilio_phone_number: Optional[str] = None
    created_at: datetime


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE


class UserCreate(UserBase):
    password: str
    tenant_id: Optional[str] = None


class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: Optional[str] = None
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    status: UserStatus
    tenant_id: Optional[str] = None


class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[EmailStr] = None
    preferred_channel: PreferredChannel = PreferredChannel.SMS
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class Customer(CustomerBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PropertyBase(BaseModel):
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    property_type: PropertyType = PropertyType.RESIDENTIAL
    system_type: Optional[str] = None
    install_date: Optional[str] = None
    last_service_date: Optional[str] = None
    notes: Optional[str] = None


class PropertyCreate(PropertyBase):
    customer_id: str


class Property(PropertyBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TechnicianBase(BaseModel):
    name: str
    phone: str
    email: Optional[EmailStr] = None
    active: bool = True
    skills: List[str] = []


class TechnicianCreate(TechnicianBase):
    pass


class Technician(TechnicianBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class LeadBase(BaseModel):
    source: LeadSource
    channel: LeadChannel
    status: LeadStatus = LeadStatus.NEW
    issue_type: Optional[str] = None
    urgency: Urgency = Urgency.ROUTINE
    description: Optional[str] = None
    tags: List[str] = []
    caller_name: Optional[str] = None  # Store caller name directly on lead
    caller_phone: Optional[str] = None  # Store caller phone directly on lead


class LeadCreate(LeadBase):
    customer_id: Optional[str] = None
    property_id: Optional[str] = None


class Lead(LeadBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: Optional[str] = None
    property_id: Optional[str] = None
    first_contact_at: datetime = Field(default_factory=utc_now)
    last_activity_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class JobBase(BaseModel):
    job_type: JobType
    priority: JobPriority = JobPriority.NORMAL
    service_window_start: datetime
    service_window_end: datetime
    exact_arrival_time: Optional[datetime] = None
    status: JobStatus = JobStatus.BOOKED
    assigned_technician_id: Optional[str] = None
    created_by: JobCreatedBy = JobCreatedBy.STAFF
    notes: Optional[str] = None
    quote_amount: Optional[float] = None  # Estimated cost for the job
    quote_id: Optional[str] = None  # Link to quote if generated


class JobCreate(JobBase):
    customer_id: str
    property_id: str
    lead_id: Optional[str] = None


class Job(JobBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: str
    property_id: str
    lead_id: Optional[str] = None
    reminder_day_before_sent: bool = False
    reminder_morning_of_sent: bool = False
    en_route_sms_sent: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class QuoteBase(BaseModel):
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    status: QuoteStatus = QuoteStatus.DRAFT


class QuoteCreate(QuoteBase):
    customer_id: str
    property_id: str
    job_id: Optional[str] = None


class Quote(QuoteBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: str
    property_id: str
    job_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InvoiceBase(BaseModel):
    amount: float
    currency: str = "USD"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    due_date: str


class InvoiceCreate(InvoiceBase):
    customer_id: str
    job_id: str


class Invoice(InvoiceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: str
    job_id: str
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ConversationBase(BaseModel):
    primary_channel: PreferredChannel = PreferredChannel.SMS
    status: ConversationStatus = ConversationStatus.OPEN


class Conversation(ConversationBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: str
    lead_id: Optional[str] = None
    last_message_from: Optional[SenderType] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MessageBase(BaseModel):
    direction: MessageDirection
    sender_type: SenderType
    channel: PreferredChannel = PreferredChannel.SMS
    content: str
    metadata: Optional[dict] = None
    is_call_summary: bool = False


class MessageCreate(MessageBase):
    conversation_id: str
    customer_id: str
    lead_id: Optional[str] = None


class Message(MessageBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    conversation_id: str
    customer_id: str
    lead_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class CampaignBase(BaseModel):
    name: str
    type: CampaignType
    status: CampaignStatus = CampaignStatus.DRAFT
    segment_definition: Optional[dict] = None
    message_template: Optional[str] = None


class CampaignCreate(CampaignBase):
    pass


class Campaign(CampaignBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CampaignRecipient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    campaign_id: str
    customer_id: str
    property_id: Optional[str] = None
    status: RecipientStatus = RecipientStatus.PENDING
    last_message_at: Optional[datetime] = None
    response: Optional[str] = None


# ============= REVIEW MODELS =============

class ReviewBase(BaseModel):
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    job_id: str


class Review(ReviewBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    customer_id: str
    job_id: str
    created_at: datetime = Field(default_factory=utc_now)


# ============= AUTH MODELS =============

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============= VAPI MODELS =============

class VapiCreateLeadRequest(BaseModel):
    tenant_slug: str
    # Support both field naming conventions
    caller_phone: Optional[str] = None
    caller_number: Optional[str] = None  # Alias for caller_phone
    caller_name: Optional[str] = None
    captured_name: Optional[str] = None  # Alias for caller_name
    captured_email: Optional[str] = None  # Optional email
    issue_type: Optional[str] = None
    issue_description: Optional[str] = None  # Alias for description
    urgency: Optional[str] = "ROUTINE"
    description: Optional[str] = None
    # Address fields - support both formats
    address_line1: Optional[str] = None
    captured_address: Optional[str] = None  # Alias - will be parsed
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None


class VapiCheckAvailabilityRequest(BaseModel):
    tenant_slug: str
    date: str  # YYYY-MM-DD
    job_type: Optional[str] = "DIAGNOSTIC"


class VapiBookJobRequest(BaseModel):
    tenant_slug: str
    lead_id: str
    customer_id: str
    property_id: str
    job_type: str
    window_start: str  # ISO datetime
    window_end: str


class VapiSendSmsRequest(BaseModel):
    tenant_slug: str
    to_phone: str
    message: str


class VapiCallSummaryRequest(BaseModel):
    tenant_slug: str
    lead_id: str
    summary: str
    vapi_session_id: Optional[str] = None


class WebFormLeadRequest(BaseModel):
    """Request model for web form lead submission"""
    tenant_slug: str
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    issue_description: str
    urgency: Optional[str] = "ROUTINE"  # EMERGENCY, URGENT, ROUTINE
    preferred_date: Optional[str] = None
    preferred_time: Optional[str] = None
    send_confirmation_sms: bool = True


# ============= SUBSCRIPTION / BILLING MODELS =============

class PlanTier(str, Enum):
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

class SubscriptionStatus(str, Enum):
    INACTIVE = "INACTIVE"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    UNPAID = "UNPAID"

class TenantSubscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    plan: PlanTier = PlanTier.STARTER
    status: SubscriptionStatus = SubscriptionStatus.TRIALING
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_checkout_session_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
