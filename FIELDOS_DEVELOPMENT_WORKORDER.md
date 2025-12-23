# FieldOS Development Work Order & Technical Specification

**Document Version:** 1.0  
**Created:** December 19, 2024  
**Project:** FieldOS - AI-Powered Service Business Operating System  
**Target Price Point:** $499-999/month per tenant

---

# TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Current System State](#2-current-system-state)
3. [Phase 1: Revenue Loop Completion](#3-phase-1-revenue-loop-completion)
4. [Phase 2: Customer Experience & Retention](#4-phase-2-customer-experience--retention)
5. [Phase 3: Cost Optimization & Premium Features](#5-phase-3-cost-optimization--premium-features)
6. [Phase 4: Multi-Industry Expansion](#6-phase-4-multi-industry-expansion)
7. [Database Schema Reference](#7-database-schema-reference)
8. [API Endpoint Reference](#8-api-endpoint-reference)
9. [Testing Requirements](#9-testing-requirements)
10. [Deployment Checklist](#10-deployment-checklist)

---

# 1. EXECUTIVE SUMMARY

## 1.1 Business Objective

Transform FieldOS into a premium AI-first service business operating system that justifies $500+/month pricing by:
- Closing the revenue loop (quotes → invoices → payments)
- Automating customer experience touchpoints
- Reducing operational costs (Vapi/Twilio/OpenAI)
- Expanding to multi-industry support

## 1.2 Technical Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11) |
| Frontend | React 18 + Tailwind CSS + Shadcn UI |
| Database | MongoDB (Motor async driver) |
| Authentication | JWT tokens |
| Voice AI | Vapi (Phase 1-2) → Self-hosted (Phase 3) |
| SMS | Twilio |
| Payments | Stripe |
| AI/LLM | OpenAI GPT-4o / GPT-4o-mini |

## 1.3 Phase Overview

| Phase | Focus | Timeline | Priority Features |
|-------|-------|----------|-------------------|
| 1 | Revenue Loop | 2-3 weeks | Invoicing, Stripe Payments, Payment Tracking |
| 2 | Retention | 2-3 weeks | Review Requests, On-My-Way, Job Completion Flow |
| 3 | Cost & Premium | 3-4 weeks | Self-hosted Voice AI, White-label, Customer Portal |
| 4 | Multi-Industry | 2-3 weeks | Industry Templates, Custom Fields, Workflow Builder |

---

# 2. CURRENT SYSTEM STATE

## 2.1 Existing Database Collections

```
tenants          - Multi-tenant organization data
users            - User accounts with roles (OWNER, ADMIN, TECH)
customers        - End customers of tenants
properties       - Service locations/addresses
leads            - Lead intake from Vapi, webform, SMS
jobs             - Service appointments/jobs
quotes           - Price quotes attached to jobs
invoices         - Basic invoice structure (needs enhancement)
technicians      - Service technicians
conversations    - SMS conversation threads
messages         - Individual SMS messages
campaigns        - Marketing campaigns
campaign_recipients - Campaign target list
```

## 2.2 Existing API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Current user info

### Core CRUD
- `/api/v1/customers` - Full CRUD + bulk delete
- `/api/v1/properties` - Full CRUD
- `/api/v1/leads` - Full CRUD + bulk delete
- `/api/v1/jobs` - Full CRUD + bulk delete + en-route
- `/api/v1/quotes` - CRUD
- `/api/v1/invoices` - Basic CRUD (needs enhancement)
- `/api/v1/technicians` - CRUD
- `/api/v1/conversations` - CRUD + messages
- `/api/v1/campaigns` - Full campaign management

### Vapi Integration (AI Receptionist)
- `POST /api/v1/vapi/create-lead` - Create lead from voice call
- `POST /api/v1/vapi/check-availability` - Check schedule availability
- `POST /api/v1/vapi/book-job` - Book service appointment
- `POST /api/v1/vapi/send-sms` - Send SMS to customer
- `POST /api/v1/vapi/call-summary` - Store call summary

### Other
- `POST /api/v1/webform/submit` - Web form lead intake with AI SMS booking
- `POST /api/v1/sms/inbound` - Twilio webhook for incoming SMS
- `GET /api/v1/dashboard` - Dashboard metrics
- `GET /api/v1/dispatch/board` - Dispatch board data
- `GET /api/v1/analytics/overview` - Reports data
- `/api/v1/portal/*` - Basic customer portal (needs enhancement)

## 2.3 Existing Frontend Pages

| Page | Route | Status |
|------|-------|--------|
| Login | `/login` | ✅ Complete |
| Dashboard | `/` | ✅ Complete |
| Leads | `/leads` | ✅ Complete |
| Jobs | `/jobs` | ✅ Complete |
| Customers | `/customers` | ✅ Complete |
| Calendar | `/calendar` | ✅ Complete |
| Dispatch | `/dispatch` | ✅ Complete |
| Quotes | `/quotes` | ✅ Complete (needs invoice link) |
| Reports | `/reports` | ✅ Complete |
| Campaigns | `/campaigns` | ✅ Complete |
| Inbox | `/inbox` | ✅ Complete |
| Settings | `/settings` | 🟡 Basic |
| Technicians | `/technicians` | ✅ Complete |
| Customer Portal | `/portal/:token` | 🟡 Basic |
| Admin Tenants | `/admin/tenants` | ✅ Complete |

## 2.4 Current Integrations

| Integration | Status | Notes |
|-------------|--------|-------|
| Vapi | ✅ Active | AI voice receptionist |
| Twilio | ✅ Active | SMS send/receive |
| OpenAI | ✅ Active | AI SMS responses |
| Stripe | ❌ Not integrated | Phase 1 priority |

---

# 3. PHASE 1: REVENUE LOOP COMPLETION

**Objective:** Enable tenants to get paid through FieldOS by converting quotes to invoices and accepting payments.

**Timeline:** 2-3 weeks  
**Priority:** CRITICAL

---

## 3.1 Feature: Enhanced Invoicing System

### 3.1.1 Requirements

1. Convert quote to invoice with one click
2. Add line items to invoices (labor, materials, fees)
3. Apply discounts (percentage or fixed)
4. Calculate taxes (configurable tax rate per tenant)
5. Track invoice status: DRAFT → SENT → VIEWED → PAID → OVERDUE
6. Send invoice via SMS and email
7. Auto-generate invoice numbers (tenant-specific sequence)
8. Support partial payments
9. Payment reminders (manual and automated)

### 3.1.2 Database Schema Changes

```javascript
// invoices collection - ENHANCED
{
  id: "uuid",
  tenant_id: "uuid",
  customer_id: "uuid",
  property_id: "uuid",
  job_id: "uuid",           // Link to job
  quote_id: "uuid",         // Link to original quote
  
  // Invoice identification
  invoice_number: "INV-2024-0001",  // Auto-generated
  
  // Line items
  line_items: [
    {
      id: "uuid",
      type: "LABOR" | "MATERIAL" | "FEE" | "DISCOUNT",
      description: "Diagnostic service",
      quantity: 1,
      unit_price: 89.00,
      total: 89.00
    }
  ],
  
  // Calculations
  subtotal: 339.00,
  discount_type: "PERCENTAGE" | "FIXED" | null,
  discount_value: 10,       // 10% or $10
  discount_amount: 33.90,
  tax_rate: 8.25,           // Percentage
  tax_amount: 25.17,
  total: 330.27,
  
  // Payment tracking
  amount_paid: 0.00,
  amount_due: 330.27,
  
  // Status
  status: "DRAFT" | "SENT" | "VIEWED" | "PARTIALLY_PAID" | "PAID" | "OVERDUE" | "CANCELLED",
  
  // Dates
  invoice_date: "2024-12-19T00:00:00Z",
  due_date: "2024-12-29T00:00:00Z",   // Net 10 default
  sent_at: null,
  viewed_at: null,
  paid_at: null,
  
  // Payment info
  payments: [
    {
      id: "uuid",
      amount: 100.00,
      method: "CARD" | "BANK" | "CASH" | "CHECK",
      stripe_payment_id: "pi_xxx",
      paid_at: "2024-12-20T14:30:00Z",
      notes: ""
    }
  ],
  
  // Communication
  reminder_sent_at: null,
  reminder_count: 0,
  
  // Metadata
  notes: "",
  internal_notes: "",
  created_at: "2024-12-19T00:00:00Z",
  updated_at: "2024-12-19T00:00:00Z"
}

// NEW: invoice_settings embedded in tenants collection
{
  // Add to tenants collection
  invoice_settings: {
    default_payment_terms: 10,        // Days until due
    default_tax_rate: 8.25,
    invoice_prefix: "INV",
    next_invoice_number: 1,
    company_name: "Radiance HVAC",
    company_address: "123 Main St, Philadelphia, PA 19103",
    company_phone: "+12155551234",
    company_email: "billing@radiancehvac.com",
    company_logo_url: "",
    invoice_footer_text: "Thank you for your business!",
    payment_instructions: "Pay online or call us to pay by phone.",
    auto_reminder_enabled: true,
    auto_reminder_days: [3, 7, 14],   // Days after due date
  }
}
```

### 3.1.3 API Endpoints

```
# Invoice CRUD (Enhanced)
GET    /api/v1/invoices                    - List invoices with filters
GET    /api/v1/invoices/:id                - Get invoice details
POST   /api/v1/invoices                    - Create new invoice
PUT    /api/v1/invoices/:id                - Update invoice
DELETE /api/v1/invoices/:id                - Delete invoice (draft only)

# Invoice Actions
POST   /api/v1/invoices/:id/send           - Send invoice to customer (SMS + email)
POST   /api/v1/invoices/:id/remind         - Send payment reminder
POST   /api/v1/invoices/:id/mark-paid      - Manually mark as paid (cash/check)
POST   /api/v1/invoices/:id/record-payment - Record partial payment
POST   /api/v1/invoices/:id/void           - Void/cancel invoice

# Quote to Invoice
POST   /api/v1/quotes/:id/convert-to-invoice  - Convert quote to invoice

# Invoice Settings
GET    /api/v1/settings/invoice            - Get invoice settings
PUT    /api/v1/settings/invoice            - Update invoice settings

# Public Invoice View (no auth required)
GET    /api/v1/invoice-view/:token         - View invoice (customer facing)
POST   /api/v1/invoice-view/:token/pay     - Initiate payment
```

### 3.1.4 API Specifications

#### POST /api/v1/invoices

**Request Body:**
```json
{
  "customer_id": "uuid",
  "property_id": "uuid",
  "job_id": "uuid",
  "quote_id": "uuid",
  "line_items": [
    {
      "type": "LABOR",
      "description": "Diagnostic service",
      "quantity": 1,
      "unit_price": 89.00
    },
    {
      "type": "MATERIAL",
      "description": "Air filter replacement",
      "quantity": 2,
      "unit_price": 25.00
    }
  ],
  "discount_type": "PERCENTAGE",
  "discount_value": 10,
  "tax_rate": 8.25,
  "due_date": "2024-12-29",
  "notes": "Thank you for choosing us!"
}
```

**Response:**
```json
{
  "id": "uuid",
  "invoice_number": "INV-2024-0001",
  "customer": { ... },
  "line_items": [ ... ],
  "subtotal": 139.00,
  "discount_amount": 13.90,
  "tax_amount": 10.32,
  "total": 135.42,
  "amount_due": 135.42,
  "status": "DRAFT",
  "payment_link": "https://fieldos.com/pay/abc123"
}
```

#### POST /api/v1/invoices/:id/send

**Request Body:**
```json
{
  "send_sms": true,
  "send_email": true,
  "custom_message": "Hi {first_name}, your invoice is ready!"
}
```

**Response:**
```json
{
  "success": true,
  "sms_sent": true,
  "email_sent": true,
  "invoice": { ... }
}
```

**SMS Message Template:**
```
Hi {first_name}, your invoice #{invoice_number} for ${total} is ready. 
View and pay: {payment_link}
Due by {due_date}.
```

#### POST /api/v1/quotes/:id/convert-to-invoice

**Request Body:**
```json
{
  "additional_line_items": [],
  "discount_type": null,
  "discount_value": 0,
  "due_days": 10,
  "send_immediately": true
}
```

**Response:**
```json
{
  "success": true,
  "invoice": { ... },
  "sms_sent": true
}
```

### 3.1.5 Frontend Components

#### InvoicesPage.js (`/invoices`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Invoices                                    [+ New Invoice] │
├─────────────────────────────────────────────────────────────┤
│ Filters: [Status ▼] [Date Range] [Search...]               │
├─────────────────────────────────────────────────────────────┤
│ Summary Cards:                                              │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│ │Outstanding│ │ Overdue  │ │  Paid    │ │  Draft   │       │
│ │ $2,450   │ │  $890    │ │ $12,340  │ │   3      │       │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│ Invoice Table:                                              │
│ ┌─────────┬──────────┬─────────┬─────────┬────────┬──────┐ │
│ │ Invoice │ Customer │ Amount  │ Status  │ Due    │ Act  │ │
│ ├─────────┼──────────┼─────────┼─────────┼────────┼──────┤ │
│ │INV-0001 │ John S.  │ $330.27 │ ● SENT  │ Dec 29 │ ⋮    │ │
│ │INV-0002 │ Mary J.  │ $125.00 │ ● PAID  │ Dec 25 │ ⋮    │ │
│ │INV-0003 │ Bob K.   │ $89.00  │ ● OVER  │ Dec 15 │ ⋮    │ │
│ └─────────┴──────────┴─────────┴─────────┴────────┴──────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Status Colors:**
- DRAFT: Gray
- SENT: Blue
- VIEWED: Yellow
- PARTIALLY_PAID: Orange
- PAID: Green
- OVERDUE: Red
- CANCELLED: Gray strikethrough

#### CreateInvoiceModal.js

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Create Invoice                                        [X]   │
├─────────────────────────────────────────────────────────────┤
│ Customer: [Search/Select Customer ▼]                        │
│ Property: [Select Property ▼]                               │
│ Job:      [Select Job (optional) ▼]                         │
├─────────────────────────────────────────────────────────────┤
│ Line Items:                                                 │
│ ┌────────┬────────────────────┬─────┬─────────┬──────────┐ │
│ │ Type   │ Description        │ Qty │ Price   │ Total    │ │
│ ├────────┼────────────────────┼─────┼─────────┼──────────┤ │
│ │ Labor  │ Diagnostic service │ 1   │ $89.00  │ $89.00   │ │
│ │ Material│ Air filter        │ 2   │ $25.00  │ $50.00   │ │
│ │        │                    │     │         │          │ │
│ └────────┴────────────────────┴─────┴─────────┴──────────┘ │
│ [+ Add Line Item]                                           │
├─────────────────────────────────────────────────────────────┤
│                                     Subtotal:    $139.00    │
│ Discount: [Type ▼] [Value]          Discount:    -$13.90    │
│ Tax Rate: [8.25]%                   Tax:         $10.32     │
│                                     ─────────────────────── │
│                                     Total:       $135.42    │
├─────────────────────────────────────────────────────────────┤
│ Due Date: [Dec 29, 2024]                                    │
│ Notes: [                                                  ] │
├─────────────────────────────────────────────────────────────┤
│                          [Cancel]  [Save Draft] [Send Now]  │
└─────────────────────────────────────────────────────────────┘
```

#### InvoiceDetailModal.js

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Invoice #INV-2024-0001                   [Send] [⋮ More]    │
├─────────────────────────────────────────────────────────────┤
│ Status: ● SENT                                              │
│                                                             │
│ Customer: John Smith              Due Date: Dec 29, 2024    │
│ Phone: (215) 555-1234            Created: Dec 19, 2024     │
│ Email: john@example.com          Sent: Dec 19, 2024        │
│                                                             │
│ Property: 123 Main St, Philadelphia, PA 19103               │
│ Job: #JOB-0045 - HVAC Diagnostic                           │
├─────────────────────────────────────────────────────────────┤
│ Line Items:                                                 │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Diagnostic service (Labor)           1 × $89.00  $89.00│ │
│ │ Air filter (Material)                2 × $25.00  $50.00│ │
│ └────────────────────────────────────────────────────────┘ │
│                                                             │
│                                     Subtotal:    $139.00    │
│                                     Discount (10%): -$13.90 │
│                                     Tax (8.25%):   $10.32   │
│                                     ─────────────────────── │
│                                     Total:       $135.42    │
│                                     Paid:         $0.00     │
│                                     Balance Due: $135.42    │
├─────────────────────────────────────────────────────────────┤
│ Payment History:                                            │
│ No payments recorded                                        │
├─────────────────────────────────────────────────────────────┤
│ [Record Payment] [Send Reminder] [Copy Payment Link]        │
└─────────────────────────────────────────────────────────────┘
```

### 3.1.6 Business Logic

1. **Invoice Number Generation:**
   - Format: `{prefix}-{year}-{sequence}` (e.g., INV-2024-0001)
   - Sequence is tenant-specific and auto-increments
   - Store `next_invoice_number` in tenant settings

2. **Quote to Invoice Conversion:**
   - Copy quote amount as single line item OR
   - If job has `quote_amount`, use job type as description
   - Set status to DRAFT initially
   - Option to send immediately

3. **Invoice Status Flow:**
   ```
   DRAFT → SENT → VIEWED → PAID
                ↓
            OVERDUE (auto-set when past due_date)
                ↓
            PAID (when fully paid)
   ```

4. **Overdue Processing:**
   - Background job runs daily at midnight tenant time
   - Mark invoices as OVERDUE if: status = SENT|VIEWED AND due_date < today
   - Send auto-reminder if enabled in settings

5. **Partial Payments:**
   - When payment received < amount_due:
     - Add to payments array
     - Update amount_paid
     - Update amount_due
     - Set status to PARTIALLY_PAID
   - When amount_paid >= total:
     - Set status to PAID
     - Set paid_at timestamp

---

## 3.2 Feature: Stripe Payment Integration

### 3.2.1 Requirements

1. Accept credit/debit card payments
2. Accept ACH bank transfers
3. Generate secure payment links
4. Process payments via customer portal
5. Handle webhooks for payment confirmation
6. Support refunds
7. Store payment history
8. PCI-compliant (use Stripe Checkout/Elements)

### 3.2.2 Environment Variables

```env
# Add to backend/.env
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_CONNECT_ENABLED=false
```

### 3.2.3 Database Schema Changes

```javascript
// Add to tenants collection
{
  stripe_settings: {
    stripe_account_id: "acct_xxx",     // For Stripe Connect (future)
    stripe_enabled: true,
    payment_methods: ["card", "us_bank_account"],
    statement_descriptor: "RADIANCE HVAC"
  }
}

// Add to invoices collection
{
  // Payment link
  stripe_payment_intent_id: "pi_xxx",
  stripe_checkout_session_id: "cs_xxx",
  payment_link_token: "abc123def456",
  payment_link_expires_at: "2024-12-29T23:59:59Z",
  
  // In payments array
  payments: [
    {
      id: "uuid",
      amount: 135.42,
      method: "CARD",
      stripe_payment_intent_id: "pi_xxx",
      stripe_charge_id: "ch_xxx",
      card_last4: "4242",
      card_brand: "visa",
      paid_at: "2024-12-20T14:30:00Z",
      receipt_url: "https://pay.stripe.com/receipts/xxx"
    }
  ]
}
```

### 3.2.4 API Endpoints

```
# Payment Processing
POST   /api/v1/invoices/:id/create-payment-link   - Generate Stripe payment link
POST   /api/v1/invoices/:id/create-checkout       - Create Stripe Checkout session
GET    /api/v1/invoices/:id/payment-status        - Check payment status

# Stripe Webhooks
POST   /api/v1/webhooks/stripe                    - Handle Stripe events

# Public Payment Page
GET    /api/v1/pay/:token                         - Get invoice for payment
POST   /api/v1/pay/:token/checkout                - Create checkout session
GET    /api/v1/pay/:token/success                 - Payment success redirect
GET    /api/v1/pay/:token/cancel                  - Payment cancelled redirect

# Refunds
POST   /api/v1/invoices/:id/refund                - Process refund
```

### 3.2.5 API Specifications

#### POST /api/v1/invoices/:id/create-checkout

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_xxx",
  "session_id": "cs_xxx",
  "expires_at": "2024-12-19T15:30:00Z"
}
```

#### POST /api/v1/webhooks/stripe

**Handle Events:**
- `checkout.session.completed` - Mark invoice as paid
- `payment_intent.succeeded` - Record payment
- `payment_intent.payment_failed` - Log failure
- `charge.refunded` - Record refund

**Webhook Handler Logic:**
```python
@app.post("/api/v1/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        invoice_id = session["metadata"]["invoice_id"]
        
        # Update invoice
        await db.invoices.update_one(
            {"id": invoice_id},
            {
                "$set": {
                    "status": "PAID",
                    "paid_at": datetime.now(timezone.utc).isoformat()
                },
                "$push": {
                    "payments": {
                        "id": str(uuid4()),
                        "amount": session["amount_total"] / 100,
                        "method": "CARD",
                        "stripe_payment_intent_id": session["payment_intent"],
                        "paid_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        )
        
        # Send confirmation SMS
        # ... SMS logic ...
    
    return {"received": True}
```

### 3.2.6 Frontend Components

#### PaymentPage.js (`/pay/:token`) - Public, No Auth

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│              [Company Logo]                                 │
│              Radiance HVAC                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│              Invoice #INV-2024-0001                         │
│                                                             │
│              Amount Due: $135.42                            │
│              Due Date: December 29, 2024                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│              ┌─────────────────────────────┐               │
│              │       Pay Now - $135.42     │               │
│              │   [Credit Card] [Bank]      │               │
│              └─────────────────────────────┘               │
│                                                             │
│              ┌─────────────────────────────┐               │
│              │    View Invoice Details     │               │
│              └─────────────────────────────┘               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Secure payments powered by Stripe                    🔒     │
└─────────────────────────────────────────────────────────────┘
```

**After Payment:**
```
┌─────────────────────────────────────────────────────────────┐
│              [Company Logo]                                 │
│              Radiance HVAC                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    ✓ Payment Successful                     │
│                                                             │
│              Invoice #INV-2024-0001                         │
│              Amount Paid: $135.42                           │
│                                                             │
│              A receipt has been sent to your phone.         │
│                                                             │
│              ┌─────────────────────────────┐               │
│              │      Download Receipt       │               │
│              └─────────────────────────────┘               │
│                                                             │
│              Thank you for your business!                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2.7 Payment Link Generation

**Token Generation:**
```python
def generate_payment_token(invoice_id: str) -> str:
    """Generate secure, time-limited payment token"""
    import secrets
    import hashlib
    
    random_bytes = secrets.token_bytes(16)
    hash_input = f"{invoice_id}:{random_bytes.hex()}:{datetime.now().isoformat()}"
    token = hashlib.sha256(hash_input.encode()).hexdigest()[:24]
    
    return token
```

**Payment Link Format:**
```
https://{tenant_subdomain}.fieldos.com/pay/{token}
OR
https://app.fieldos.com/pay/{token}
```

---

## 3.3 Feature: Automated Payment Flow

### 3.3.1 Job Completion → Invoice → Payment Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Job         │ --> │ Invoice     │ --> │ Payment     │
│ COMPLETED   │     │ Created     │     │ Link Sent   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Customer    │
                    │ Pays Online │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Invoice     │
                    │ Marked PAID │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Review      │
                    │ Request     │
                    └─────────────┘
```

### 3.3.2 Auto-Invoice on Job Completion

When job status changes to COMPLETED:

1. Check if invoice already exists for this job
2. If not, create invoice from quote_amount
3. Mark invoice as SENT
4. Send payment link via SMS:

```
Hi {first_name}, thanks for choosing {company_name}! 

Your service is complete. Invoice #{invoice_number} for ${total} is ready.

Pay securely: {payment_link}

Questions? Reply to this text.
```

### 3.3.3 Payment Confirmation SMS

When payment is received:

```
Hi {first_name}, we received your payment of ${amount} for invoice #{invoice_number}. 

Thank you for your business!

Receipt: {receipt_url}
```

---

## 3.4 Implementation Checklist - Phase 1

### Backend Tasks

- [ ] **3.4.1** Enhance Invoice model in `models.py`
  - Add line_items, payments, calculations fields
  - Add InvoiceCreate, InvoiceUpdate, InvoiceResponse schemas

- [ ] **3.4.2** Create invoice utility functions
  - `generate_invoice_number(tenant_id)`
  - `calculate_invoice_totals(line_items, discount, tax_rate)`
  - `generate_payment_token(invoice_id)`

- [ ] **3.4.3** Update/create invoice endpoints in `server.py`
  - Enhanced CRUD operations
  - `/send`, `/remind`, `/record-payment` actions
  - `/create-checkout` Stripe integration

- [ ] **3.4.4** Create quote-to-invoice endpoint
  - `POST /api/v1/quotes/:id/convert-to-invoice`

- [ ] **3.4.5** Implement Stripe integration
  - Install `stripe` package
  - Add Stripe API key to `.env`
  - Create checkout session endpoint
  - Create webhook handler

- [ ] **3.4.6** Create public payment endpoints
  - `GET /api/v1/pay/:token`
  - `POST /api/v1/pay/:token/checkout`

- [ ] **3.4.7** Add invoice settings to tenant
  - Update tenant model
  - Create settings endpoints

- [ ] **3.4.8** Add auto-invoice on job completion
  - Update `PUT /api/v1/jobs/:id` to trigger invoice
  - Send SMS with payment link

- [ ] **3.4.9** Create background job for overdue processing
  - Check invoices daily
  - Update status to OVERDUE
  - Send reminder if enabled

### Frontend Tasks

- [ ] **3.4.10** Create InvoicesPage component
  - Table with filters and search
  - Summary cards (outstanding, overdue, paid)

- [ ] **3.4.11** Create CreateInvoiceModal component
  - Customer/property selection
  - Line item management
  - Calculations display

- [ ] **3.4.12** Create InvoiceDetailModal component
  - Full invoice view
  - Payment history
  - Action buttons

- [ ] **3.4.13** Create public PaymentPage component
  - Invoice display
  - Stripe Checkout integration
  - Success/cancel handling

- [ ] **3.4.14** Add "Convert to Invoice" button to QuotesPage

- [ ] **3.4.15** Add invoice link to JobsPage when invoice exists

- [ ] **3.4.16** Update navigation to include Invoices page

- [ ] **3.4.17** Add invoice settings to SettingsPage

### Testing Tasks

- [ ] **3.4.18** Test invoice CRUD operations
- [ ] **3.4.19** Test quote to invoice conversion
- [ ] **3.4.20** Test Stripe checkout flow
- [ ] **3.4.21** Test webhook handling
- [ ] **3.4.22** Test payment link expiration
- [ ] **3.4.23** Test overdue processing
- [ ] **3.4.24** Test partial payments

---

# 4. PHASE 2: CUSTOMER EXPERIENCE & RETENTION

**Objective:** Increase customer satisfaction and retention through automated touchpoints.

**Timeline:** 2-3 weeks  
**Priority:** HIGH

---

## 4.1 Feature: "On My Way" Technician Tracking

### 4.1.1 Requirements

1. Technician marks "En Route" in app
2. Customer receives SMS with:
   - Technician name and photo (optional)
   - Estimated arrival time
   - Link to live tracking page (optional)
3. Auto-calculate ETA based on distance (Google Maps API or simple estimate)
4. Update customer if delayed

### 4.1.2 Database Schema Changes

```javascript
// Add to jobs collection
{
  en_route_at: "2024-12-19T14:00:00Z",
  estimated_arrival: "2024-12-19T14:25:00Z",
  actual_arrival: null,
  tech_location_updated_at: null,
  tracking_enabled: true
}

// Add to technicians collection
{
  photo_url: "https://...",
  vehicle_info: "White Ford Transit - ABC123",
  current_location: {
    lat: 39.9526,
    lng: -75.1652,
    updated_at: "2024-12-19T14:05:00Z"
  }
}
```

### 4.1.3 API Endpoints

```
# Technician Actions
POST   /api/v1/jobs/:id/en-route           - Mark en route (exists, enhance)
POST   /api/v1/jobs/:id/arrived            - Mark arrived on site
POST   /api/v1/jobs/:id/update-eta         - Update ETA if delayed

# Customer Tracking (public)
GET    /api/v1/track/:token                - Get tracking info for customer
```

### 4.1.4 API Specifications

#### POST /api/v1/jobs/:id/en-route (Enhanced)

**Request Body:**
```json
{
  "technician_id": "uuid",
  "estimated_minutes": 25,
  "send_sms": true,
  "include_tracking_link": true
}
```

**Response:**
```json
{
  "success": true,
  "job": { ... },
  "sms_sent": true,
  "tracking_token": "track_abc123"
}
```

**SMS Message:**
```
Hi {first_name}! {tech_name} from {company_name} is on the way. 

Estimated arrival: {eta_time} ({estimated_minutes} mins)

Track: {tracking_link}
```

### 4.1.5 Frontend Components

#### TrackingPage.js (`/track/:token`) - Public

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│              [Company Logo]                                 │
│              Radiance HVAC                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌─────────┐                                             │
│    │  Photo  │  Mike Johnson                                │
│    │  here   │  Service Technician                          │
│    └─────────┘  White Ford Transit                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│              🚗 On the way!                                 │
│                                                             │
│              Estimated arrival: 2:25 PM                     │
│              (About 20 minutes)                             │
│                                                             │
│    ┌─────────────────────────────────────────────────┐     │
│    │                                                 │     │
│    │              [Map showing route]                │     │
│    │                                                 │     │
│    └─────────────────────────────────────────────────┘     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Service: HVAC Diagnostic                                    │
│ Address: 123 Main St, Philadelphia, PA                      │
│ Scheduled: 2:00 PM - 4:00 PM                               │
├─────────────────────────────────────────────────────────────┤
│ Questions? Call: (215) 555-1234                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 4.2 Feature: Automated Review Requests

### 4.2.1 Requirements

1. Trigger review request after job completion + payment
2. Wait configurable delay (e.g., 2 hours after completion)
3. Send SMS with direct links to Google/Yelp/Facebook
4. Track if review was requested and if customer responded
5. One request per job (no spam)
6. Option to disable per customer

### 4.2.2 Database Schema Changes

```javascript
// Add to jobs collection
{
  review_requested_at: null,
  review_request_sent: false,
  review_received: false,
  review_platform: null,        // "GOOGLE", "YELP", "FACEBOOK"
  review_rating: null           // 1-5 if captured
}

// Add to tenants collection (settings)
{
  review_settings: {
    enabled: true,
    delay_hours: 2,             // Hours after completion to send
    google_review_url: "https://g.page/r/xxx/review",
    yelp_review_url: "https://yelp.com/biz/xxx",
    facebook_review_url: "https://facebook.com/xxx/reviews",
    preferred_platform: "GOOGLE",
    message_template: "Hi {first_name}, thank you for choosing {company_name}! We'd love your feedback. Please leave us a review: {review_link}"
  }
}

// Add to customers collection
{
  review_opt_out: false,
  last_review_requested_at: null,
  review_request_count: 0
}
```

### 4.2.3 API Endpoints

```
# Review Management
POST   /api/v1/jobs/:id/request-review     - Manually trigger review request
GET    /api/v1/reviews/pending             - List jobs pending review request
GET    /api/v1/reviews/stats               - Review request statistics

# Settings
GET    /api/v1/settings/reviews            - Get review settings
PUT    /api/v1/settings/reviews            - Update review settings

# Customer opt-out
POST   /api/v1/customers/:id/review-opt-out - Opt customer out of reviews
```

### 4.2.4 Review Request SMS

**Template:**
```
Hi {first_name}! Thanks for choosing {company_name}. 

We hope you're happy with your {job_type} service today. We'd really appreciate a quick review!

⭐ Leave a review: {review_link}

It only takes a minute and helps us grow. Thank you!
```

**Short Version (if needed):**
```
Hi {first_name}! Thanks for your business today. We'd love a review! ⭐ {review_link}
```

### 4.2.5 Background Job: Review Request Processor

```python
async def process_review_requests():
    """Run every 30 minutes to send pending review requests"""
    
    # Find jobs completed X hours ago that haven't had review requested
    cutoff = datetime.now(timezone.utc) - timedelta(hours=delay_hours)
    
    jobs = await db.jobs.find({
        "status": "COMPLETED",
        "completed_at": {"$lte": cutoff.isoformat()},
        "review_request_sent": {"$ne": True}
    }).to_list(100)
    
    for job in jobs:
        customer = await db.customers.find_one({"id": job["customer_id"]})
        
        # Skip if customer opted out
        if customer.get("review_opt_out"):
            continue
        
        # Skip if requested review from this customer recently (30 days)
        if customer.get("last_review_requested_at"):
            last_request = datetime.fromisoformat(customer["last_review_requested_at"])
            if (datetime.now(timezone.utc) - last_request).days < 30:
                continue
        
        # Send review request
        await send_review_request(job, customer)
        
        # Update records
        await db.jobs.update_one(
            {"id": job["id"]},
            {"$set": {
                "review_request_sent": True,
                "review_requested_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await db.customers.update_one(
            {"id": customer["id"]},
            {
                "$set": {"last_review_requested_at": datetime.now(timezone.utc).isoformat()},
                "$inc": {"review_request_count": 1}
            }
        )
```

---

## 4.3 Feature: Job Completion Workflow

### 4.3.1 Requirements

1. Tech marks job as "Complete" in app
2. System automatically:
   - Creates invoice (if doesn't exist)
   - Sends invoice + payment link to customer
   - Schedules review request
3. Option to collect signature/photos before completion
4. Job summary sent to customer

### 4.3.2 Job Completion Flow

```
Tech marks COMPLETE
       │
       ▼
┌─────────────────┐
│ Capture:        │
│ - Photos        │
│ - Notes         │
│ - Signature     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Auto-create     │
│ Invoice         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Send Customer:  │
│ - Summary SMS   │
│ - Invoice       │
│ - Payment link  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Schedule:       │
│ - Review request│
│   (after delay) │
└─────────────────┘
```

### 4.3.3 API Endpoint

#### POST /api/v1/jobs/:id/complete

**Request Body:**
```json
{
  "technician_id": "uuid",
  "completion_notes": "Replaced air filter, cleaned coils, tested system",
  "photos": [
    {
      "type": "BEFORE",
      "url": "https://..."
    },
    {
      "type": "AFTER", 
      "url": "https://..."
    }
  ],
  "signature_url": "https://...",
  "additional_charges": [
    {
      "description": "Additional refrigerant",
      "amount": 75.00
    }
  ],
  "send_invoice": true,
  "request_review": true
}
```

**Response:**
```json
{
  "success": true,
  "job": { ... },
  "invoice": { ... },
  "invoice_sent": true,
  "review_scheduled": true,
  "review_send_at": "2024-12-19T18:00:00Z"
}
```

### 4.3.4 Job Completion SMS

```
Hi {first_name}, your {job_type} service is complete!

Summary:
{completion_notes}

Invoice #{invoice_number}: ${total}
Pay: {payment_link}

Thank you for choosing {company_name}!
```

---

## 4.4 Implementation Checklist - Phase 2

### Backend Tasks

- [ ] **4.4.1** Add tracking fields to Job model
- [ ] **4.4.2** Add location fields to Technician model
- [ ] **4.4.3** Enhance `/en-route` endpoint with SMS
- [ ] **4.4.4** Create `/arrived` endpoint
- [ ] **4.4.5** Create public tracking endpoint
- [ ] **4.4.6** Add review settings to Tenant model
- [ ] **4.4.7** Add review fields to Job model
- [ ] **4.4.8** Create review request endpoints
- [ ] **4.4.9** Create background job for review requests
- [ ] **4.4.10** Create `/complete` endpoint with full flow
- [ ] **4.4.11** Integrate completion → invoice → payment → review

### Frontend Tasks

- [ ] **4.4.12** Create TrackingPage component
- [ ] **4.4.13** Add "On My Way" button to dispatch board
- [ ] **4.4.14** Create JobCompletionModal with photos/notes/signature
- [ ] **4.4.15** Add review settings to SettingsPage
- [ ] **4.4.16** Show review status on Jobs list

### Testing Tasks

- [ ] **4.4.17** Test en-route SMS flow
- [ ] **4.4.18** Test tracking page
- [ ] **4.4.19** Test review request scheduling
- [ ] **4.4.20** Test job completion flow
- [ ] **4.4.21** Test opt-out functionality

---

# 5. PHASE 3: COST OPTIMIZATION & PREMIUM FEATURES

**Objective:** Reduce operational costs and add premium features to justify $500+ pricing.

**Timeline:** 3-4 weeks  
**Priority:** HIGH

---

## 5.1 Feature: Self-Hosted Voice AI (Replace Vapi)

### 5.1.1 Cost Comparison

| Component | Vapi | Self-Hosted |
|-----------|------|-------------|
| Per minute | $0.15 | ~$0.05 |
| Monthly (3000 mins) | $450 | $150 |
| Savings | - | $300/month |

### 5.1.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INBOUND CALL                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   TWILIO VOICE                              │
│                  (Receives call)                            │
│                   $0.014/min                                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               TWILIO MEDIA STREAMS                          │
│              (WebSocket audio stream)                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              FASTAPI WEBSOCKET SERVER                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Whisper    │  │   GPT-4o     │  │  OpenAI TTS  │     │
│  │    STT       │→ │   Brain      │→ │   Voice      │     │
│  │  $0.006/min  │  │  $0.01/call  │  │  $0.03/resp  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  AUDIO RESPONSE                             │
│               (Back to Twilio/caller)                       │
└─────────────────────────────────────────────────────────────┘
```

### 5.1.3 Implementation Components

#### 5.1.3.1 Twilio Voice Webhook

```python
@app.post("/api/v1/voice/inbound")
async def voice_inbound(request: Request):
    """Handle inbound call from Twilio"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_phone = form_data.get("From")
    to_phone = form_data.get("To")
    
    # Look up tenant by phone number
    tenant = await db.tenants.find_one({"twilio_phone_number": to_phone})
    
    if not tenant:
        # Return TwiML to reject call
        return Response(
            content='<Response><Say>Sorry, this number is not configured.</Say></Response>',
            media_type="application/xml"
        )
    
    # Generate TwiML to connect to WebSocket
    websocket_url = f"wss://{request.host}/api/v1/voice/stream/{call_sid}"
    
    twiml = f"""
    <Response>
        <Connect>
            <Stream url="{websocket_url}">
                <Parameter name="tenant_id" value="{tenant['id']}" />
                <Parameter name="from_phone" value="{from_phone}" />
            </Stream>
        </Connect>
    </Response>
    """
    
    return Response(content=twiml, media_type="application/xml")
```

#### 5.1.3.2 WebSocket Audio Handler

```python
@app.websocket("/api/v1/voice/stream/{call_sid}")
async def voice_stream(websocket: WebSocket, call_sid: str):
    """Handle real-time audio stream from Twilio"""
    await websocket.accept()
    
    # Initialize services
    from services.voice_ai_service import VoiceAIService
    voice_ai = VoiceAIService()
    
    # Get parameters from stream
    tenant_id = None
    from_phone = None
    
    try:
        while True:
            message = await websocket.receive_json()
            
            if message["event"] == "start":
                # Extract parameters
                tenant_id = message["start"]["customParameters"]["tenant_id"]
                from_phone = message["start"]["customParameters"]["from_phone"]
                
                # Initialize conversation
                await voice_ai.initialize(tenant_id, from_phone, call_sid)
                
                # Send greeting
                greeting_audio = await voice_ai.get_greeting()
                await websocket.send_json({
                    "event": "media",
                    "streamSid": message["start"]["streamSid"],
                    "media": {"payload": greeting_audio}
                })
                
            elif message["event"] == "media":
                # Receive audio chunk
                audio_chunk = base64.b64decode(message["media"]["payload"])
                
                # Process through STT
                transcript = await voice_ai.process_audio(audio_chunk)
                
                if transcript:
                    # Got complete utterance, generate response
                    response_audio = await voice_ai.generate_response(transcript)
                    
                    # Send audio back
                    await websocket.send_json({
                        "event": "media",
                        "streamSid": message["streamSid"],
                        "media": {"payload": response_audio}
                    })
                    
            elif message["event"] == "stop":
                # Call ended
                await voice_ai.end_conversation()
                break
                
    except WebSocketDisconnect:
        await voice_ai.end_conversation()
```

#### 5.1.3.3 Voice AI Service

```python
# /app/backend/services/voice_ai_service.py

import openai
from openai import AsyncOpenAI
import base64
import io

class VoiceAIService:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.conversation_history = []
        self.tenant = None
        self.customer = None
        self.audio_buffer = b""
        
    async def initialize(self, tenant_id: str, from_phone: str, call_sid: str):
        """Initialize conversation context"""
        # Load tenant
        self.tenant = await db.tenants.find_one({"id": tenant_id})
        
        # Find or create customer
        self.customer = await db.customers.find_one({"phone": from_phone})
        
        # Build system prompt
        self.system_prompt = f"""
        You are a friendly AI receptionist for {self.tenant['name']}.
        
        Your job is to:
        1. Greet the caller warmly
        2. Understand their service needs
        3. Collect their information (name, phone, address)
        4. Determine urgency
        5. Book a service appointment
        
        Be conversational, helpful, and efficient.
        Keep responses SHORT (1-2 sentences max) since this is a phone call.
        
        Available services: HVAC repair, maintenance, installation, diagnostic
        Service hours: Monday-Saturday 8am-7pm
        """
        
        self.call_sid = call_sid
        
    async def get_greeting(self) -> str:
        """Generate greeting audio"""
        greeting = f"Thank you for calling {self.tenant['name']}. How can I help you today?"
        
        return await self._text_to_speech(greeting)
        
    async def process_audio(self, audio_chunk: bytes) -> str | None:
        """Process audio chunk through Whisper STT"""
        self.audio_buffer += audio_chunk
        
        # Check if we have enough audio (silence detection)
        if self._detect_end_of_speech():
            # Transcribe
            audio_file = io.BytesIO(self.audio_buffer)
            audio_file.name = "audio.wav"
            
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            
            self.audio_buffer = b""
            return transcript.text
            
        return None
        
    async def generate_response(self, user_message: str) -> str:
        """Generate AI response and convert to speech"""
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Check for tool calls (book job, check availability, etc.)
        tools = self._get_available_tools()
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.system_prompt},
                *self.conversation_history
            ],
            tools=tools,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        # Handle tool calls
        if assistant_message.tool_calls:
            tool_results = await self._execute_tools(assistant_message.tool_calls)
            # Get follow-up response
            # ...
            
        # Add response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message.content
        })
        
        # Convert to speech
        return await self._text_to_speech(assistant_message.content)
        
    async def _text_to_speech(self, text: str) -> str:
        """Convert text to speech using OpenAI TTS"""
        response = await self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
            response_format="mp3"
        )
        
        audio_bytes = response.content
        return base64.b64encode(audio_bytes).decode()
        
    def _get_available_tools(self):
        """Define available function tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_lead",
                    "description": "Create a new lead/customer in the system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "address": {"type": "string"},
                            "issue_type": {"type": "string"},
                            "urgency": {"type": "string", "enum": ["EMERGENCY", "URGENT", "ROUTINE"]}
                        },
                        "required": ["name", "issue_type", "urgency"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "description": "Check available appointment slots",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
                        },
                        "required": ["date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "book_job",
                    "description": "Book a service appointment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string"},
                            "time_slot": {"type": "string", "enum": ["morning", "afternoon", "evening"]},
                            "job_type": {"type": "string"}
                        },
                        "required": ["date", "time_slot", "job_type"]
                    }
                }
            }
        ]
```

### 5.1.4 Migration Plan (Vapi → Self-Hosted)

1. **Week 1:** Build and test WebSocket infrastructure
2. **Week 2:** Implement STT/TTS pipeline with OpenAI
3. **Week 3:** Implement conversation logic and tool calling
4. **Week 4:** Testing, edge cases, fallback to Vapi if needed
5. **Week 5:** Gradual rollout (10% → 50% → 100%)

### 5.1.5 Fallback Strategy

Keep Vapi as backup:
- If WebSocket fails, fall back to Vapi
- Monitor latency/quality metrics
- A/B test call quality

---

## 5.2 Feature: White-Label Branding

### 5.2.1 Requirements

1. Custom logo on all pages
2. Custom color scheme
3. Custom email/SMS sender name
4. Custom domain support (future)
5. Remove FieldOS branding

### 5.2.2 Database Schema Changes

```javascript
// Add to tenants collection
{
  branding: {
    logo_url: "https://...",
    favicon_url: "https://...",
    primary_color: "#0066CC",
    secondary_color: "#004499",
    accent_color: "#FF6600",
    text_on_primary: "#FFFFFF",
    font_family: "Inter",
    
    // Email branding
    email_from_name: "Radiance HVAC",
    email_reply_to: "support@radiancehvac.com",
    
    // SMS branding
    sms_sender_name: "RadianceHVAC",  // If using alphanumeric sender
    
    // Portal branding
    portal_title: "Radiance HVAC Customer Portal",
    portal_welcome_message: "Welcome to your service portal",
    
    // Remove FieldOS branding
    white_label_enabled: true
  }
}
```

### 5.2.3 Frontend Implementation

```javascript
// /app/frontend/src/contexts/BrandingContext.js

import { createContext, useContext, useEffect, useState } from 'react';

const BrandingContext = createContext();

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState({
    logo_url: '/logo.png',
    primary_color: '#0066CC',
    // ... defaults
  });
  
  useEffect(() => {
    // Load branding from API
    const loadBranding = async () => {
      const response = await api.get('/settings/branding');
      setBranding(response.data);
      
      // Apply CSS custom properties
      document.documentElement.style.setProperty('--primary', response.data.primary_color);
      document.documentElement.style.setProperty('--secondary', response.data.secondary_color);
    };
    
    loadBranding();
  }, []);
  
  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  );
}

export const useBranding = () => useContext(BrandingContext);
```

---

## 5.3 Feature: Enhanced Customer Portal

### 5.3.1 Requirements

1. View service history
2. View and pay invoices
3. Approve/decline quotes
4. Request service
5. Message the company
6. Update contact info
7. View upcoming appointments

### 5.3.2 Customer Portal Routes

```
/portal/:token                    - Portal home
/portal/:token/appointments       - Upcoming & past appointments
/portal/:token/invoices           - Invoice list
/portal/:token/invoices/:id       - Invoice detail + payment
/portal/:token/quotes             - Quotes awaiting response
/portal/:token/messages           - Message history
/portal/:token/request-service    - New service request form
/portal/:token/profile            - Update contact info
```

### 5.3.3 Portal Home Layout

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]                           Welcome, John! │ [Sign Out] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Upcoming   │ │   Open      │ │  Messages   │           │
│  │ Appointment │ │  Invoices   │ │     (2)     │           │
│  │   Dec 20    │ │    $135     │ │   Unread    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Quick Actions                                               │
│                                                             │
│  [Request Service]  [Pay Invoice]  [Send Message]          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Recent Activity                                             │
│                                                             │
│  • Dec 19 - HVAC Diagnostic completed                      │
│  • Dec 19 - Invoice #INV-0001 sent ($135.42)              │
│  • Dec 18 - Appointment scheduled for Dec 20               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5.4 Implementation Checklist - Phase 3

### Self-Hosted Voice AI

- [ ] **5.4.1** Set up Twilio Voice webhook endpoint
- [ ] **5.4.2** Implement WebSocket server for audio streaming
- [ ] **5.4.3** Integrate OpenAI Whisper for STT
- [ ] **5.4.4** Integrate OpenAI TTS for speech synthesis
- [ ] **5.4.5** Implement conversation state management
- [ ] **5.4.6** Implement tool calling (create lead, book job, etc.)
- [ ] **5.4.7** Add silence detection / end-of-speech detection
- [ ] **5.4.8** Test end-to-end voice flow
- [ ] **5.4.9** Add metrics/monitoring
- [ ] **5.4.10** Implement fallback to Vapi

### White-Label Branding

- [ ] **5.4.11** Add branding fields to tenant model
- [ ] **5.4.12** Create branding settings API endpoints
- [ ] **5.4.13** Create BrandingContext in frontend
- [ ] **5.4.14** Apply dynamic CSS variables
- [ ] **5.4.15** Create branding settings UI
- [ ] **5.4.16** Update all pages to use branding context
- [ ] **5.4.17** Update email templates with branding
- [ ] **5.4.18** Update SMS templates with branding

### Enhanced Customer Portal

- [ ] **5.4.19** Create portal authentication system
- [ ] **5.4.20** Create portal home page
- [ ] **5.4.21** Create appointments page
- [ ] **5.4.22** Create invoices page with payment
- [ ] **5.4.23** Create quotes page
- [ ] **5.4.24** Create messages page
- [ ] **5.4.25** Create service request form
- [ ] **5.4.26** Create profile page
- [ ] **5.4.27** Apply white-label branding to portal

---

# 6. PHASE 4: MULTI-INDUSTRY EXPANSION

**Objective:** Transform FieldOS from field-services-only to a multi-industry platform.

**Timeline:** 2-3 weeks  
**Priority:** MEDIUM

---

## 6.1 Feature: Industry Templates

### 6.1.1 Supported Industries

| Industry | Job Types | Custom Fields |
|----------|-----------|---------------|
| HVAC | Diagnostic, Repair, Maintenance, Install | System type, Equipment age |
| Plumbing | Repair, Drain cleaning, Install, Inspection | Fixture type, Emergency |
| Electrical | Repair, Install, Inspection, Panel upgrade | Voltage, Permit needed |
| Cleaning | Standard, Deep, Move-out, Commercial | Square footage, Frequency |
| Lawn Care | Mowing, Landscaping, Fertilization, Irrigation | Lot size, Service frequency |
| Pest Control | Inspection, Treatment, Prevention | Pest type, Property type |
| Auto Detailing | Basic wash, Full detail, Interior, Ceramic | Vehicle type, Size |
| Pet Services | Walking, Sitting, Grooming | Pet type, Duration |
| Photography | Portrait, Event, Product, Real estate | Duration, Location |

### 6.1.2 Database Schema Changes

```javascript
// NEW: industry_templates collection
{
  id: "uuid",
  slug: "hvac",
  name: "HVAC",
  description: "Heating, ventilation, and air conditioning services",
  icon: "thermometer",
  
  job_types: [
    {
      slug: "diagnostic",
      name: "Diagnostic",
      description: "System inspection and diagnosis",
      base_price: 89.00,
      estimated_duration: 60  // minutes
    },
    {
      slug: "repair",
      name: "Repair",
      description: "Fix existing system issues",
      base_price: 250.00,
      estimated_duration: 120
    }
    // ...
  ],
  
  custom_fields: [
    {
      slug: "system_type",
      name: "System Type",
      type: "SELECT",
      options: ["Central AC", "Heat Pump", "Furnace", "Mini-Split", "Boiler"],
      required: false,
      applies_to: ["job", "property"]
    },
    {
      slug: "equipment_age",
      name: "Equipment Age",
      type: "NUMBER",
      unit: "years",
      required: false,
      applies_to: ["property"]
    }
  ],
  
  urgency_options: [
    { slug: "emergency", name: "Emergency", multiplier: 1.5 },
    { slug: "urgent", name: "Urgent", multiplier: 1.25 },
    { slug: "routine", name: "Routine", multiplier: 1.0 }
  ],
  
  default_settings: {
    payment_terms: 10,
    tax_rate: 8.25,
    service_hours: {
      monday: { start: "08:00", end: "19:00" },
      tuesday: { start: "08:00", end: "19:00" },
      // ...
    }
  }
}

// Update tenants collection
{
  industry_template_id: "uuid",
  industry_slug: "hvac",
  
  // Custom overrides
  custom_job_types: [],      // Additional job types
  custom_fields: [],         // Additional custom fields
  disabled_job_types: [],    // Hide certain job types
}

// Update jobs collection
{
  job_type: "diagnostic",    // Now references template
  custom_field_values: {
    system_type: "Central AC",
    equipment_age: 5
  }
}
```

### 6.1.3 API Endpoints

```
# Templates
GET    /api/v1/templates                   - List all industry templates
GET    /api/v1/templates/:slug             - Get template details

# Tenant Industry Config
GET    /api/v1/settings/industry           - Get tenant's industry config
PUT    /api/v1/settings/industry           - Update industry config
POST   /api/v1/settings/industry/job-types - Add custom job type
POST   /api/v1/settings/industry/fields    - Add custom field
```

### 6.1.4 Industry Selection UI (Onboarding)

```
┌─────────────────────────────────────────────────────────────┐
│              Welcome to FieldOS!                            │
│                                                             │
│         What type of business do you run?                   │
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │   🌡️    │ │   🔧    │ │   ⚡    │ │   🧹    │          │
│  │  HVAC   │ │Plumbing │ │Electric │ │Cleaning │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │   🌿    │ │   🐜    │ │   🚗    │ │   🐕    │          │
│  │  Lawn   │ │  Pest   │ │  Auto   │ │   Pet   │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                             │
│  ┌─────────┐ ┌─────────┐                                   │
│  │   📷    │ │   ➕    │                                   │
│  │ Photo   │ │  Other  │                                   │
│  └─────────┘ └─────────┘                                   │
│                                                             │
│         Don't see your industry? Choose "Other"            │
│         and customize everything yourself.                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6.2 Feature: Custom Fields

### 6.2.1 Requirements

1. Define custom fields per tenant
2. Apply to jobs, customers, or properties
3. Support types: TEXT, NUMBER, SELECT, MULTISELECT, DATE, BOOLEAN, FILE
4. Required vs optional
5. Show in forms and detail views
6. Include in reports

### 6.2.2 Custom Field Types

```javascript
// Field type definitions
{
  TEXT: {
    component: "Input",
    validation: "string",
    options: { maxLength: 500 }
  },
  NUMBER: {
    component: "NumberInput",
    validation: "number",
    options: { min: 0, max: null, unit: "" }
  },
  SELECT: {
    component: "Select",
    validation: "enum",
    options: { choices: [] }
  },
  MULTISELECT: {
    component: "MultiSelect",
    validation: "array",
    options: { choices: [] }
  },
  DATE: {
    component: "DatePicker",
    validation: "date",
    options: { format: "YYYY-MM-DD" }
  },
  BOOLEAN: {
    component: "Checkbox",
    validation: "boolean",
    options: {}
  },
  FILE: {
    component: "FileUpload",
    validation: "url",
    options: { maxSize: "10MB", types: ["image/*", "application/pdf"] }
  }
}
```

### 6.2.3 Custom Fields UI

```
┌─────────────────────────────────────────────────────────────┐
│ Custom Fields                                [+ Add Field]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Job Fields:                                                 │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ System Type      │ SELECT    │ Job      │ ○ Required  ▼││
│ │ Equipment Age    │ NUMBER    │ Property │ ○ Optional  ▼││
│ │ Permit Number    │ TEXT      │ Job      │ ○ Optional  ▼││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ Customer Fields:                                            │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Company Name     │ TEXT      │ Customer │ ○ Optional  ▼││
│ │ Preferred Tech   │ SELECT    │ Customer │ ○ Optional  ▼││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6.3 Feature: Workflow Builder (Future)

### 6.3.1 Concept

Allow tenants to create custom automation workflows:

```
TRIGGER: Job status changes to COMPLETED
  │
  ├─→ ACTION: Create invoice
  │
  ├─→ ACTION: Send SMS with invoice link
  │
  ├─→ DELAY: Wait 2 hours
  │
  └─→ ACTION: Send review request
```

### 6.3.2 Pre-Built Workflows

1. **Standard Completion Flow**
   - Job complete → Invoice → Payment link → Review request

2. **Appointment Reminder Flow**
   - Day before → Reminder SMS
   - 1 hour before → "On my way" reminder

3. **Quote Follow-Up Flow**
   - Quote sent → Wait 2 days → Follow-up SMS
   - Wait 5 days → Second follow-up

4. **Customer Reactivation Flow**
   - No service in 6 months → Send offer
   - No response in 7 days → Follow-up call task

---

## 6.4 Implementation Checklist - Phase 4

### Industry Templates

- [ ] **6.4.1** Create industry_templates collection
- [ ] **6.4.2** Seed initial templates (HVAC, Plumbing, Electrical, Cleaning, Lawn)
- [ ] **6.4.3** Create template API endpoints
- [ ] **6.4.4** Update tenant model with industry config
- [ ] **6.4.5** Create industry selection onboarding UI
- [ ] **6.4.6** Update job forms to use template job types
- [ ] **6.4.7** Update quote calculations with template pricing

### Custom Fields

- [ ] **6.4.8** Create custom field management API
- [ ] **6.4.9** Create custom field settings UI
- [ ] **6.4.10** Create dynamic form renderer component
- [ ] **6.4.11** Update job forms to include custom fields
- [ ] **6.4.12** Update customer forms to include custom fields
- [ ] **6.4.13** Update property forms to include custom fields
- [ ] **6.4.14** Include custom fields in exports/reports

### Workflow Builder (Future)

- [ ] **6.4.15** Design workflow data model
- [ ] **6.4.16** Create workflow execution engine
- [ ] **6.4.17** Create workflow builder UI
- [ ] **6.4.18** Implement pre-built workflow templates

---

# 7. DATABASE SCHEMA REFERENCE

## 7.1 Complete Collection Schemas

### tenants
```javascript
{
  id: String (UUID),
  name: String,
  slug: String (unique),
  subdomain: String,
  timezone: String,
  service_area: [String],
  primary_contact_name: String,
  primary_contact_email: String,
  primary_phone: String,
  booking_mode: "AUTOMATIC" | "MANUAL",
  emergency_rules: Object,
  twilio_phone_number: String,
  twilio_messaging_service_sid: String,
  tone_profile: String,
  sms_signature: String,
  
  // NEW: Invoice settings
  invoice_settings: {
    default_payment_terms: Number,
    default_tax_rate: Number,
    invoice_prefix: String,
    next_invoice_number: Number,
    company_name: String,
    company_address: String,
    company_phone: String,
    company_email: String,
    company_logo_url: String,
    invoice_footer_text: String,
    payment_instructions: String,
    auto_reminder_enabled: Boolean,
    auto_reminder_days: [Number]
  },
  
  // NEW: Stripe settings
  stripe_settings: {
    stripe_account_id: String,
    stripe_enabled: Boolean,
    payment_methods: [String],
    statement_descriptor: String
  },
  
  // NEW: Review settings
  review_settings: {
    enabled: Boolean,
    delay_hours: Number,
    google_review_url: String,
    yelp_review_url: String,
    facebook_review_url: String,
    preferred_platform: String,
    message_template: String
  },
  
  // NEW: Branding
  branding: {
    logo_url: String,
    favicon_url: String,
    primary_color: String,
    secondary_color: String,
    accent_color: String,
    text_on_primary: String,
    font_family: String,
    email_from_name: String,
    email_reply_to: String,
    sms_sender_name: String,
    portal_title: String,
    portal_welcome_message: String,
    white_label_enabled: Boolean
  },
  
  // NEW: Industry config
  industry_template_id: String,
  industry_slug: String,
  custom_job_types: [Object],
  custom_fields: [Object],
  disabled_job_types: [String],
  
  created_at: String (ISO),
  updated_at: String (ISO)
}
```

### invoices (ENHANCED)
```javascript
{
  id: String (UUID),
  tenant_id: String (UUID),
  customer_id: String (UUID),
  property_id: String (UUID),
  job_id: String (UUID),
  quote_id: String (UUID),
  
  invoice_number: String,
  
  line_items: [{
    id: String,
    type: "LABOR" | "MATERIAL" | "FEE" | "DISCOUNT",
    description: String,
    quantity: Number,
    unit_price: Number,
    total: Number
  }],
  
  subtotal: Number,
  discount_type: "PERCENTAGE" | "FIXED" | null,
  discount_value: Number,
  discount_amount: Number,
  tax_rate: Number,
  tax_amount: Number,
  total: Number,
  
  amount_paid: Number,
  amount_due: Number,
  
  status: "DRAFT" | "SENT" | "VIEWED" | "PARTIALLY_PAID" | "PAID" | "OVERDUE" | "CANCELLED",
  
  invoice_date: String (ISO),
  due_date: String (ISO),
  sent_at: String (ISO),
  viewed_at: String (ISO),
  paid_at: String (ISO),
  
  payments: [{
    id: String,
    amount: Number,
    method: "CARD" | "BANK" | "CASH" | "CHECK",
    stripe_payment_intent_id: String,
    stripe_charge_id: String,
    card_last4: String,
    card_brand: String,
    paid_at: String (ISO),
    receipt_url: String,
    notes: String
  }],
  
  stripe_checkout_session_id: String,
  payment_link_token: String,
  payment_link_expires_at: String (ISO),
  
  reminder_sent_at: String (ISO),
  reminder_count: Number,
  
  notes: String,
  internal_notes: String,
  
  created_at: String (ISO),
  updated_at: String (ISO)
}
```

### jobs (ENHANCED)
```javascript
{
  // ... existing fields ...
  
  // NEW: Completion fields
  completed_at: String (ISO),
  completion_notes: String,
  completion_photos: [{
    type: "BEFORE" | "AFTER" | "OTHER",
    url: String,
    caption: String
  }],
  signature_url: String,
  
  // NEW: Tracking fields
  en_route_at: String (ISO),
  estimated_arrival: String (ISO),
  actual_arrival: String (ISO),
  tracking_token: String,
  
  // NEW: Review fields
  review_request_sent: Boolean,
  review_requested_at: String (ISO),
  review_received: Boolean,
  review_platform: String,
  review_rating: Number,
  
  // NEW: Invoice link
  invoice_id: String (UUID),
  
  // NEW: Custom fields
  custom_field_values: Object
}
```

---

# 8. API ENDPOINT REFERENCE

## 8.1 New Endpoints Summary

### Phase 1: Revenue Loop
```
POST   /api/v1/invoices                           - Create invoice
GET    /api/v1/invoices                           - List invoices
GET    /api/v1/invoices/:id                       - Get invoice
PUT    /api/v1/invoices/:id                       - Update invoice
DELETE /api/v1/invoices/:id                       - Delete invoice
POST   /api/v1/invoices/:id/send                  - Send invoice
POST   /api/v1/invoices/:id/remind                - Send reminder
POST   /api/v1/invoices/:id/record-payment        - Record payment
POST   /api/v1/invoices/:id/create-checkout       - Create Stripe checkout
POST   /api/v1/quotes/:id/convert-to-invoice      - Convert quote to invoice
POST   /api/v1/webhooks/stripe                    - Stripe webhook
GET    /api/v1/pay/:token                         - Public payment page
POST   /api/v1/pay/:token/checkout                - Create public checkout
GET    /api/v1/settings/invoice                   - Invoice settings
PUT    /api/v1/settings/invoice                   - Update invoice settings
```

### Phase 2: Customer Experience
```
POST   /api/v1/jobs/:id/en-route                  - Mark en route (enhanced)
POST   /api/v1/jobs/:id/arrived                   - Mark arrived
POST   /api/v1/jobs/:id/complete                  - Complete job with workflow
POST   /api/v1/jobs/:id/request-review            - Request review
GET    /api/v1/track/:token                       - Public tracking page
GET    /api/v1/settings/reviews                   - Review settings
PUT    /api/v1/settings/reviews                   - Update review settings
```

### Phase 3: Premium Features
```
POST   /api/v1/voice/inbound                      - Twilio voice webhook
WS     /api/v1/voice/stream/:call_sid            - Voice WebSocket
GET    /api/v1/settings/branding                  - Branding settings
PUT    /api/v1/settings/branding                  - Update branding
GET    /api/v1/portal/:token/*                    - Enhanced portal routes
```

### Phase 4: Multi-Industry
```
GET    /api/v1/templates                          - List industry templates
GET    /api/v1/templates/:slug                    - Get template
GET    /api/v1/settings/industry                  - Industry settings
PUT    /api/v1/settings/industry                  - Update industry settings
POST   /api/v1/settings/custom-fields             - Add custom field
PUT    /api/v1/settings/custom-fields/:id         - Update custom field
DELETE /api/v1/settings/custom-fields/:id         - Delete custom field
```

---

# 9. TESTING REQUIREMENTS

## 9.1 Unit Tests

### Phase 1
- [ ] Invoice number generation
- [ ] Invoice total calculations
- [ ] Payment token generation
- [ ] Stripe webhook signature verification
- [ ] Overdue status calculation

### Phase 2
- [ ] ETA calculation
- [ ] Review request scheduling
- [ ] Opt-out filtering

### Phase 3
- [ ] Audio chunk processing
- [ ] Speech-to-text conversion
- [ ] Tool calling logic
- [ ] Branding CSS variable application

### Phase 4
- [ ] Template loading
- [ ] Custom field validation
- [ ] Dynamic form generation

## 9.2 Integration Tests

### Phase 1
- [ ] Full invoice creation flow
- [ ] Quote to invoice conversion
- [ ] Stripe checkout flow
- [ ] Payment webhook processing
- [ ] Auto-invoice on job completion

### Phase 2
- [ ] En-route SMS flow
- [ ] Tracking page data
- [ ] Review request flow
- [ ] Complete job workflow

### Phase 3
- [ ] Voice call end-to-end
- [ ] Portal authentication
- [ ] Portal invoice payment

### Phase 4
- [ ] Industry template application
- [ ] Custom field CRUD
- [ ] Form rendering with custom fields

## 9.3 E2E Tests

- [ ] Customer receives invoice, pays, gets receipt
- [ ] Tech marks en-route, customer sees tracking
- [ ] Job completed, invoice sent, review requested
- [ ] New tenant onboards with industry template

---

# 10. DEPLOYMENT CHECKLIST

## 10.1 Environment Variables

```env
# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Optional: Google Maps for ETA
GOOGLE_MAPS_API_KEY=xxx

# Voice AI (Phase 3)
TWILIO_VOICE_WEBHOOK_URL=https://xxx/api/v1/voice/inbound
```

## 10.2 Database Migrations

1. Add new fields to existing collections
2. Create new indexes:
   - `invoices.payment_link_token` (unique)
   - `invoices.status` + `invoices.due_date`
   - `jobs.tracking_token` (unique)
3. Seed industry templates

## 10.3 Stripe Setup

1. Create Stripe account
2. Get API keys
3. Set up webhook endpoint
4. Configure webhook events:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.refunded`

## 10.4 Twilio Setup (Voice - Phase 3)

1. Configure voice webhook URL
2. Enable Media Streams
3. Test with ngrok locally

---

# APPENDIX A: FILE STRUCTURE

```
/app
├── backend/
│   ├── server.py                 # Main API (modify)
│   ├── models.py                 # Pydantic models (modify)
│   ├── services/
│   │   ├── twilio_service.py     # Existing (modify)
│   │   ├── ai_sms_service.py     # Existing
│   │   ├── stripe_service.py     # NEW
│   │   ├── voice_ai_service.py   # NEW (Phase 3)
│   │   └── review_service.py     # NEW
│   ├── utils/
│   │   ├── invoice_utils.py      # NEW
│   │   └── tracking_utils.py     # NEW
│   └── templates/                # NEW - Email templates
│       ├── invoice_email.html
│       └── review_request.html
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── invoices/
│       │   │   └── InvoicesPage.js      # NEW
│       │   ├── payment/
│       │   │   └── PaymentPage.js       # NEW (public)
│       │   ├── tracking/
│       │   │   └── TrackingPage.js      # NEW (public)
│       │   ├── portal/
│       │   │   └── CustomerPortal.js    # ENHANCE
│       │   └── settings/
│       │       └── SettingsPage.js      # ENHANCE
│       ├── components/
│       │   ├── invoices/
│       │   │   ├── CreateInvoiceModal.js
│       │   │   ├── InvoiceDetailModal.js
│       │   │   └── InvoiceTable.js
│       │   └── shared/
│       │       └── CustomFieldRenderer.js  # NEW (Phase 4)
│       └── contexts/
│           └── BrandingContext.js       # NEW (Phase 3)
└── FIELDOS_DEVELOPMENT_WORKORDER.md     # This document
```

---

# APPENDIX B: GLOSSARY

| Term | Definition |
|------|------------|
| Tenant | A business/company using FieldOS |
| Customer | End customer of a tenant |
| Lead | Initial contact/inquiry from a customer |
| Job | Scheduled service appointment |
| Quote | Price estimate for a job |
| Invoice | Bill sent to customer for payment |
| Conversation | SMS thread with a customer |
| Campaign | Marketing outreach to multiple customers |

---

**END OF WORK ORDER**

*Document maintained by FieldOS Development Team*
*Last updated: December 19, 2024*
