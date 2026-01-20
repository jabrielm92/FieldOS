# FieldOS - Product Requirements Document

## Original Problem Statement
Build a multi-tenant web application called "FieldOS," a Revenue & Operations OS for field service companies. The platform should enable lead capture, job booking, communications, quotes, campaigns, and integrate with AI voice/SMS for automated booking and customer interactions.

## Strategic Vision
Create a premium "AI-First & Multi-Industry" platform that justifies a ~$500/month price point through significant automation and operational cost reduction. The platform competes with established players like Housecall Pro by offering:
- Self-hosted Voice AI (70-80% cost savings vs third-party)
- White-label branding for agencies
- Multi-industry templates

## Technology Stack
- **Backend:** FastAPI (Python) on port 8001
- **Frontend:** React with Shadcn/UI on port 3000
- **Database:** MongoDB
- **Integrations:** Twilio (SMS/Voice + ConversationRelay), OpenAI (via Emergent LLM Key)

## Deployment
- **Backend:** Railway (supports WebSockets for ConversationRelay)
- **Frontend:** Vercel
- **Database:** MongoDB Atlas
- See `/backend/DEPLOY_RAILWAY.md` and `/frontend/DEPLOY_VERCEL.md`

---

## COMPLETED FEATURES

### Phase 0: Core Platform (Complete)
- [x] Multi-tenant architecture with tenant isolation
- [x] JWT authentication with role-based access (OWNER, MANAGER, TECHNICIAN)
- [x] Full CRUD for: Leads, Customers, Properties, Jobs, Quotes, Technicians
- [x] Interactive Calendar with drag-and-drop scheduling
- [x] Dispatch Board with real-time job status
- [x] Dashboard with KPIs and analytics
- [x] Reports page with revenue tracking
- [x] Campaigns module with bulk SMS

### Phase 0.5: AI Integrations (Complete)
- [x] Vapi Voice AI integration for inbound calls
- [x] AI-powered SMS booking flow (webform → conversation → booking)
- [x] Automated quote generation on job booking
- [x] Automated SMS confirmations with quote amounts
- [x] Phone number normalization (E.164 format)
- [x] Data deduplication for jobs and conversations

### Phase 3: Premium Features (Complete - January 2026)
- [x] **White-Label Branding**
  - [x] Logo, favicon, colors (primary, secondary, accent)
  - [x] Font family selection
  - [x] Email and SMS sender customization
  - [x] Portal title and welcome message
  - [x] Custom domain placeholder (with setup instructions)
  - [x] White-label toggle to remove FieldOS branding

- [x] **Enhanced Customer Portal**
  - [x] Navigation tabs: Home, Appointments, Invoices, History, Messages
  - [x] Branding dynamically applied from tenant settings
  - [x] Quick actions: Request Service, Pay Invoice, Send Message, Call
  - [x] Service request form (issue, urgency, property, preferred date/time)
  - [x] View pending quotes with Accept/Decline
  - [x] Service history with job status and invoice info
  - [x] Message history view
  - [x] Profile editing (name, email, phone)

- [x] **Self-Hosted Voice AI with ConversationRelay (January 2026)**
  - [x] Twilio ConversationRelay for real-time WebSocket streaming
  - [x] Google TTS (en-US-Casual-K voice) - natural, conversational
  - [x] OpenAI GPT-4o-mini for NLU via Emergent LLM Key
  - [x] Real-time speech processing (no HTTP round-trip latency)
  - [x] Interruptible TTS (barge-in support)
  - [x] Conversation flow: Name → Phone → Address → Issue → Urgency → Book
  - [x] Auto-create customer, property, lead, and job on booking
  - [x] SMS confirmation sent automatically
  - [x] Cost: $0.07/min (ConversationRelay) + OpenAI tokens (~70% cheaper than Vapi)

- [x] **Service Requests Management**
  - [x] List service requests from customer portal
  - [x] Convert service requests to booked jobs
  - [x] Auto-create lead and quote on conversion
  - [x] SMS confirmation sent to customer

### Superadmin Dashboard (Complete - January 2026)
- [x] **Tenant Management**
  - [x] Create tenants with owner accounts
  - [x] Edit tenant settings (name, contact, timezone, tone profile)
  - [x] Delete tenants with all associated data
  - [x] View storage/document usage per tenant

- [x] **Voice AI Onboarding (Admin)**
  - [x] Configure Twilio credentials per tenant (Account SID, Auth Token, API Keys)
  - [x] Configure OpenAI API key per tenant
  - [x] Configure ElevenLabs API key and Voice ID per tenant
  - [x] Set voice provider (ElevenLabs or Twilio TTS)
  - [x] Customize greeting message and system prompt per tenant
  - [x] Set after-hours message per tenant
  - [x] Enable/disable Voice AI per tenant

- [x] **Tenant Settings Page (Owner View)**
  - [x] Company settings auto-populated from tenant data
  - [x] Branding customization (logo, colors, fonts)
  - [x] Customer portal configuration
  - [x] Messaging settings (SMS signature, email from name)
  - [x] Scheduling preferences (booking mode, emergency rules)

---

## PENDING FEATURES

### Phase 1: Revenue Loop (P1 - Next)
- [ ] Invoicing system (Quote → Invoice)
- [ ] Stripe payment integration
- [ ] Invoice payment tracking (Paid, Unpaid, Overdue)
- [ ] Payment link generation in portal

### Phase 2: Customer Experience (P2)
- [ ] "On My Way" automated texts with ETA
- [ ] Post-job review request workflow
- [ ] Google/Yelp review link generation
- [ ] Job completion checklist

### Phase 4: Multi-Industry (P3)
- [ ] Industry-specific templates (HVAC, Plumbing, Cleaning, Lawn Care)
- [ ] Custom fields per industry
- [ ] Workflow builder

---

## API ENDPOINTS

### Authentication
- POST /api/v1/auth/login
- POST /api/v1/auth/register

### Branding (Authenticated)
- GET /api/v1/settings/branding
- PUT /api/v1/settings/branding

### Customer Portal (Public - token-based)
- GET /api/v1/portal/{token}
- GET /api/v1/portal/{token}/branding
- GET /api/v1/portal/{token}/messages
- GET /api/v1/portal/{token}/invoices
- GET /api/v1/portal/{token}/service-history
- POST /api/v1/portal/{token}/request-service
- PUT /api/v1/portal/{token}/profile
- POST /api/v1/portal/{token}/quote/{quote_id}/respond
- POST /api/v1/portal/{token}/reschedule-request
- POST /api/v1/portal/{token}/add-note
- POST /api/v1/portal/{token}/review

### Service Requests (Authenticated)
- GET /api/v1/service-requests
- POST /api/v1/service-requests/{id}/convert

### Voice AI Webhooks
- POST /api/v1/voice/inbound
- POST /api/v1/voice/recording-complete
- POST /api/v1/voice/status
- WebSocket /api/v1/voice/stream/{call_sid}

---

## DATABASE COLLECTIONS
- tenants (with branding field)
- users
- customers
- properties
- leads
- jobs
- quotes
- invoices
- conversations
- messages
- campaigns
- campaign_recipients
- technicians
- reviews
- service_requests (NEW)

---

## TEST CREDENTIALS
- Email: owner@radiancehvac.com
- Password: owner123
- Portal Token: 2279f98d-WJviWzBjvXf-mBSaQlwJjQ

---

## KEY FILES
- /app/backend/server.py - Main API
- /app/backend/models.py - Data models
- /app/backend/services/voice_ai_service.py - Self-hosted voice AI
- /app/backend/services/ai_sms_service.py - AI SMS conversations
- /app/backend/services/twilio_service.py - Twilio SMS
- /app/frontend/src/pages/settings/SettingsPage.js - Branding settings
- /app/frontend/src/pages/portal/CustomerPortal.js - Customer portal
- /app/FIELDOS_DEVELOPMENT_WORKORDER.md - Full development plan

---

Last Updated: January 9, 2026
