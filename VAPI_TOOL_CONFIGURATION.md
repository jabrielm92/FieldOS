# Vapi Tool Configuration for FieldOS

**Last Updated:** December 18, 2025  
**Backend Base URL:** `https://bizvoice-4.preview.emergentagent.com`

---

## Quick Reference - All URLs

| Tool | URL |
|------|-----|
| **Create Lead** | `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/create-lead` |
| **Check Availability** | `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/check-availability` |
| **Book Job** | `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/book-job` |
| **Send SMS** | `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/send-sms` |
| **Log Call Summary** | `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/call-summary` |
| **Twilio Inbound SMS Webhook** | `https://bizvoice-4.preview.emergentagent.com/api/v1/sms/inbound` |

---

## ⚠️ CRITICAL: Fixing the Date Issue

The AI doesn't inherently know today's date. To fix this, you MUST inject the current date into your Vapi assistant's system prompt.

### Option 1: Use Vapi's Built-in {{now}} Variable (Recommended)

In your Vapi assistant's **System Prompt**, add at the very beginning:

```
CURRENT DATE: {{now}}

When converting relative dates to YYYY-MM-DD format:
- "today" = the date shown above
- "tomorrow" = add 1 day
- "next week" = add 7 days  
- "next Monday" = calculate from current date above
```

### Option 2: Use Custom Dynamic Variables via API

When starting a call via Vapi API, pass the current date:

```javascript
const response = await vapi.calls.create({
  assistantId: "your-assistant-id",
  customer: { number: "+1234567890" },
  assistantOverrides: {
    variableValues: {
      current_date: new Date().toISOString().split('T')[0],
      current_date_formatted: new Date().toLocaleDateString('en-US', { 
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
      })
    }
  }
});
```

Then in your system prompt:
```
Today is {{current_date_formatted}} ({{current_date}}).
```

### Option 3: Server URL for Dynamic System Prompt

Create an endpoint that returns the system prompt with current date injected, then use Vapi's "Server URL" feature for the system prompt.

---

## Authentication Header (Required for ALL Vapi tools)

All Vapi tool requests must include this header:

```
x-vapi-secret: service-hub-258
```

---

## Tool 1: Create Lead

**Purpose:** Create a new lead and customer record when a caller provides their information.

**URL:** `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/create-lead`  
**Method:** POST  
**Content-Type:** application/json

### Request Body
```json
{
  "tenant_slug": "radiance-hvac",
  "caller_name": "John Smith",
  "caller_phone": "+12155551234",
  "captured_address": "123 Main St, Philadelphia, PA 19001",
  "description": "Heating system not turning on",
  "urgency": "EMERGENCY"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_slug` | string | Yes | Always use `radiance-hvac` |
| `caller_name` | string | Yes | Customer's full name |
| `caller_phone` | string | Yes | Phone number (with country code preferred) |
| `captured_address` | string | No | Full address as single string (will be parsed) |
| `description` | string | No | Description of the issue |
| `urgency` | string | No | One of: `EMERGENCY`, `URGENT`, `ROUTINE` (default: ROUTINE) |
| `captured_email` | string | No | Customer's email address |

### Response Example
```json
{
  "result": "success",
  "status": "lead_created",
  "lead_id": "abc123-def456",
  "customer_id": "cust-789",
  "property_id": "prop-012",
  "conversation_id": "conv-345",
  "customer_name": "John",
  "instructions": "IMPORTANT: The lead has been successfully created in the system. The customer John is now registered. Their customer ID is cust-789. You should now ask the customer what date they would like to schedule their service appointment, then call the check-availability tool with that date."
}
```

### Vapi Tool Definition
```json
{
  "type": "function",
  "function": {
    "name": "create-lead",
    "description": "Create a new lead in the system after collecting customer information. Call this after getting the customer's name, phone number, address, and issue description.",
    "parameters": {
      "type": "object",
      "properties": {
        "tenant_slug": {
          "type": "string",
          "description": "The tenant identifier. Always use 'radiance-hvac'",
          "default": "radiance-hvac"
        },
        "caller_name": {
          "type": "string",
          "description": "The customer's full name"
        },
        "caller_phone": {
          "type": "string",
          "description": "The customer's phone number"
        },
        "captured_address": {
          "type": "string",
          "description": "The full service address including street, city, state, and ZIP code"
        },
        "description": {
          "type": "string",
          "description": "Description of the service issue"
        },
        "urgency": {
          "type": "string",
          "enum": ["EMERGENCY", "URGENT", "ROUTINE"],
          "description": "How urgent is this service request"
        }
      },
      "required": ["tenant_slug", "caller_name", "caller_phone"]
    }
  },
  "server": {
    "url": "https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/create-lead",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 2: Check Availability

**Purpose:** Check available appointment slots for a given date.

**URL:** `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/check-availability`  
**Method:** POST  
**Content-Type:** application/json

### Request Body
```json
{
  "tenant_slug": "radiance-hvac",
  "date": "2025-12-19"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_slug` | string | Yes | Always use `radiance-hvac` |
| `date` | string | Yes | Date in YYYY-MM-DD format, OR "today", "tomorrow" |

### Response Example
```json
{
  "result": "success",
  "status": "slots_available",
  "date": "2025-12-19",
  "date_formatted": "Friday, December 19, 2025",
  "current_server_date": "2025-12-18",
  "current_server_date_formatted": "Thursday, December 18, 2025",
  "windows": [
    {
      "date": "2025-12-19",
      "start": "08:00",
      "end": "12:00",
      "label": "Morning (8am-12pm)",
      "available": true,
      "window_start": "2025-12-19T08:00:00",
      "window_end": "2025-12-19T12:00:00"
    },
    {
      "date": "2025-12-19",
      "start": "12:00",
      "end": "17:00",
      "label": "Afternoon (12pm-5pm)",
      "available": true,
      "window_start": "2025-12-19T12:00:00",
      "window_end": "2025-12-19T17:00:00"
    }
  ],
  "has_availability": true,
  "available_slots": "Morning (8am-12pm), Afternoon (12pm-5pm)",
  "instructions": "IMPORTANT: Good news! For Friday, December 19, 2025, the following time slots are available: Morning (8am-12pm), Afternoon (12pm-5pm). Tell the customer these options and ask which one works best for them. Once they choose, call the book-job tool using the window_start and window_end values from the chosen slot to complete the booking. Remember: Today is Thursday, December 18, 2025."
}
```

### Vapi Tool Definition
```json
{
  "type": "function",
  "function": {
    "name": "check-availability",
    "description": "Check available appointment time slots for a specific date. Use YYYY-MM-DD format for the date. You can also pass 'today' or 'tomorrow'. The response includes current server date for reference.",
    "parameters": {
      "type": "object",
      "properties": {
        "tenant_slug": {
          "type": "string",
          "description": "The tenant identifier. Always use 'radiance-hvac'",
          "default": "radiance-hvac"
        },
        "date": {
          "type": "string",
          "description": "The date to check in YYYY-MM-DD format (e.g., '2025-12-19'), or 'today', or 'tomorrow'"
        }
      },
      "required": ["tenant_slug", "date"]
    }
  },
  "server": {
    "url": "https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/check-availability",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 3: Book Job

**Purpose:** Book a service appointment after the customer selects a time slot.

**URL:** `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/book-job`  
**Method:** POST  
**Content-Type:** application/json

### Request Body
```json
{
  "tenant_slug": "radiance-hvac",
  "lead_id": "abc123-def456",
  "customer_id": "cust-789",
  "property_id": "prop-012",
  "job_type": "DIAGNOSTIC",
  "window_start": "2025-12-19T08:00:00",
  "window_end": "2025-12-19T12:00:00"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_slug` | string | Yes | Always use `radiance-hvac` |
| `lead_id` | string | Yes | From create-lead response |
| `customer_id` | string | Yes | From create-lead response |
| `property_id` | string | Yes | From create-lead response |
| `job_type` | string | Yes | One of: `DIAGNOSTIC`, `REPAIR`, `MAINTENANCE`, `INSTALLATION` |
| `window_start` | string | Yes | ISO datetime from check-availability `window_start` |
| `window_end` | string | Yes | ISO datetime from check-availability `window_end` |

### Response Example
```json
{
  "result": "success",
  "status": "job_booked",
  "job_id": "job-567",
  "service_window": "Friday, December 19 from 08:00 AM to 12:00 PM",
  "confirmation_sms_sent": true,
  "instructions": "IMPORTANT: Great news! The appointment has been successfully booked for John on Friday, December 19 from 08:00 AM to 12:00 PM. A confirmation text message has been sent to the customer. Ask if there's anything else you can help with today."
}
```

### Vapi Tool Definition
```json
{
  "type": "function",
  "function": {
    "name": "book-job",
    "description": "Book a service appointment after the customer has selected a time slot. Use the lead_id, customer_id, and property_id from the create-lead response, and the window_start and window_end from the check-availability response.",
    "parameters": {
      "type": "object",
      "properties": {
        "tenant_slug": {
          "type": "string",
          "description": "The tenant identifier. Always use 'radiance-hvac'",
          "default": "radiance-hvac"
        },
        "lead_id": {
          "type": "string",
          "description": "The lead ID returned from create-lead"
        },
        "customer_id": {
          "type": "string",
          "description": "The customer ID returned from create-lead"
        },
        "property_id": {
          "type": "string",
          "description": "The property ID returned from create-lead"
        },
        "job_type": {
          "type": "string",
          "enum": ["DIAGNOSTIC", "REPAIR", "MAINTENANCE", "INSTALLATION"],
          "description": "The type of service job",
          "default": "DIAGNOSTIC"
        },
        "window_start": {
          "type": "string",
          "description": "The start time of the service window in ISO format (from check-availability window_start)"
        },
        "window_end": {
          "type": "string",
          "description": "The end time of the service window in ISO format (from check-availability window_end)"
        }
      },
      "required": ["tenant_slug", "lead_id", "customer_id", "property_id", "job_type", "window_start", "window_end"]
    }
  },
  "server": {
    "url": "https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/book-job",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 4: Send SMS

**Purpose:** Send an SMS message to a customer (optional, for custom messages).

**URL:** `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/send-sms`  
**Method:** POST  
**Content-Type:** application/json

### Request Body
```json
{
  "tenant_slug": "radiance-hvac",
  "to_phone": "+12155551234",
  "message": "Thank you for calling Radiance HVAC! We look forward to serving you."
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_slug` | string | Yes | Always use `radiance-hvac` |
| `to_phone` | string | Yes | Customer's phone number |
| `message` | string | Yes | The SMS message content |

### Vapi Tool Definition
```json
{
  "type": "function",
  "function": {
    "name": "send-sms",
    "description": "Send an SMS text message to a customer. Note: Confirmation SMS is automatically sent when booking a job, so this is only needed for custom messages.",
    "parameters": {
      "type": "object",
      "properties": {
        "tenant_slug": {
          "type": "string",
          "description": "The tenant identifier. Always use 'radiance-hvac'",
          "default": "radiance-hvac"
        },
        "to_phone": {
          "type": "string",
          "description": "The customer's phone number to send SMS to"
        },
        "message": {
          "type": "string",
          "description": "The message content to send"
        }
      },
      "required": ["tenant_slug", "to_phone", "message"]
    }
  },
  "server": {
    "url": "https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/send-sms",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 5: Log Call Summary

**Purpose:** Log a summary of the call for record-keeping (typically called at end of call).

**URL:** `https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/call-summary`  
**Method:** POST  
**Content-Type:** application/json

### Request Body
```json
{
  "tenant_slug": "radiance-hvac",
  "lead_id": "abc123-def456",
  "summary": "Customer called about heating system not working. Emergency priority. Booked for tomorrow morning 8am-12pm."
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_slug` | string | Yes | Always use `radiance-hvac` |
| `lead_id` | string | Yes | The lead ID from create-lead |
| `summary` | string | Yes | Summary of the call |

### Vapi Tool Definition
```json
{
  "type": "function",
  "function": {
    "name": "log-call-summary",
    "description": "Log a summary of the call at the end of the conversation. Include key details like issue, urgency, and outcome.",
    "parameters": {
      "type": "object",
      "properties": {
        "tenant_slug": {
          "type": "string",
          "description": "The tenant identifier. Always use 'radiance-hvac'",
          "default": "radiance-hvac"
        },
        "lead_id": {
          "type": "string",
          "description": "The lead ID from create-lead"
        },
        "summary": {
          "type": "string",
          "description": "A summary of the call including the issue, urgency, and outcome"
        }
      },
      "required": ["tenant_slug", "lead_id", "summary"]
    }
  },
  "server": {
    "url": "https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/call-summary",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Twilio Inbound SMS Webhook

**Purpose:** Configure this in your Twilio console to receive incoming SMS messages.

**URL:** `https://bizvoice-4.preview.emergentagent.com/api/v1/sms/inbound`  
**Method:** POST  
**Content-Type:** application/x-www-form-urlencoded (Twilio's default)

### Twilio Configuration

| Setting | Value |
|---------|-------|
| **Phone Number** | `+12154843375` |
| **Messaging Service SID** | `MG174aa9ccba71d3bb841cd7c7ff6c3ba1` |

### Twilio Console Configuration

1. Go to **Twilio Console** → **Phone Numbers** → **Manage** → **Active Numbers**
2. Click on your phone number (`+12154843375`)
3. Scroll to **Messaging Configuration**
4. Under **A MESSAGE COMES IN**, set:
   - **Webhook URL:** `https://bizvoice-4.preview.emergentagent.com/api/v1/sms/inbound`
   - **HTTP Method:** POST

---

## Recommended Vapi System Prompt

**IMPORTANT:** Add `{{now}}` at the start to inject the current date dynamically.

```
## IDENTITY & ROLE
You are a friendly, professional scheduling assistant for Radiance HVAC. Your job is to help customers schedule service appointments efficiently while gathering all necessary information.

## CURRENT DATE REFERENCE
Today is {{now}}. Use this as your reference for ALL scheduling.

When customer mentions relative dates, calculate the correct YYYY-MM-DD:
- "today" → today's date
- "tomorrow" → add 1 day
- "day after tomorrow" → add 2 days  
- "next week" → add 7 days
- "next Monday/Tuesday/etc" → calculate next occurrence of that weekday

ALWAYS pass dates to check-availability in YYYY-MM-DD format.

## CALL FLOW

### Step 1: Greeting
"Thank you for calling the scheduling desk at Radiance HVAC. How can I help you today?"

### Step 2: Gather Information
Collect the following (in a conversational manner):
1. Full name
2. Best phone number to reach them (confirm if calling number is best)
3. Email (optional - ask if they'd like to add one)
4. Full service address (street, city, state, ZIP) - repeat back to confirm
5. Brief description of the issue
6. Urgency level: Ask "Is this an emergency for today, something that needs attention in the next day or two, or can it wait a few days?"

### Step 3: Create Lead
Once you have name, phone, address, and issue description, call create-lead:
- tenant_slug: "radiance-hvac"
- caller_name: [full name]
- caller_phone: [phone number]
- captured_address: [full address as single string]
- description: [issue description]
- urgency: "EMERGENCY" | "URGENT" | "ROUTINE"
- captured_email: [email if provided]

### Step 4: Schedule Appointment
Ask: "What day works best for you? Today, tomorrow, or another upcoming day?"

### Step 5: Check Availability
Call check-availability with:
- tenant_slug: "radiance-hvac"
- date: [YYYY-MM-DD format - calculate from customer's answer]

Present the available slots naturally: "We have [slots] available for [day]. Which works best for you?"

### Step 6: Book the Job
Once customer selects a slot, call book-job with:
- tenant_slug: "radiance-hvac"
- lead_id: [from create-lead response]
- customer_id: [from create-lead response]
- property_id: [from create-lead response]
- job_type: "DIAGNOSTIC" (default) or "REPAIR" | "MAINTENANCE" | "INSTALLATION"
- window_start: [from selected slot's window_start]
- window_end: [from selected slot's window_end]

### Step 7: Confirm & Close
"Your service appointment is confirmed for [date] between [time window]. You'll receive a confirmation text message shortly. Is there anything else I can help you with today?"

### Step 8: Log Summary (before ending)
Call log-call-summary with:
- tenant_slug: "radiance-hvac"
- lead_id: [from create-lead]
- summary: [Brief summary: customer name, issue, urgency, appointment date/time, address]

## COMMUNICATION STYLE
- Friendly but professional
- Confirm information back to customer
- Be patient with corrections
- Keep responses concise
- Say "one moment" when calling tools

## URGENCY CLASSIFICATION
- EMERGENCY: System completely down, safety concern, no heat in freezing weather, no AC in extreme heat
- URGENT: System partially working, needs attention within 24-48 hours
- ROUTINE: Regular maintenance, minor issues, flexible scheduling
```

---

## Testing the Tools

You can test each tool using curl:

```bash
# Test create-lead
curl -X POST "https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/create-lead" \
  -H "Content-Type: application/json" \
  -H "x-vapi-secret: service-hub-258" \
  -d '{
    "tenant_slug": "radiance-hvac",
    "caller_name": "Test User",
    "caller_phone": "+12155551234",
    "captured_address": "123 Test St, Philadelphia, PA 19001",
    "description": "AC not cooling",
    "urgency": "URGENT"
  }'

# Test check-availability (use actual YYYY-MM-DD date)
curl -X POST "https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/check-availability" \
  -H "Content-Type: application/json" \
  -H "x-vapi-secret: service-hub-258" \
  -d '{"tenant_slug": "radiance-hvac", "date": "2025-12-20"}'

# Test book-job (use IDs from create-lead and windows from check-availability)
curl -X POST "https://bizvoice-4.preview.emergentagent.com/api/v1/vapi/book-job" \
  -H "Content-Type: application/json" \
  -H "x-vapi-secret: service-hub-258" \
  -d '{
    "tenant_slug": "radiance-hvac",
    "lead_id": "YOUR_LEAD_ID",
    "customer_id": "YOUR_CUSTOMER_ID",
    "property_id": "YOUR_PROPERTY_ID",
    "job_type": "DIAGNOSTIC",
    "window_start": "2025-12-20T08:00:00",
    "window_end": "2025-12-20T12:00:00"
  }'
```
