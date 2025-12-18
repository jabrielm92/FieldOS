# Vapi Tool Configuration for FieldOS

**Last Updated:** December 18, 2025  
**Backend Base URL:** `https://service-hub-261.preview.emergentagent.com`

---

## Quick Reference - All URLs

| Tool | URL |
|------|-----|
| **Create Lead** | `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/create-lead` |
| **Check Availability** | `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/check-availability` |
| **Book Job** | `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/book-job` |
| **Send SMS** | `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/send-sms` |
| **Log Call Summary** | `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/call-summary` |
| **Twilio Inbound SMS Webhook** | `https://service-hub-261.preview.emergentagent.com/api/v1/sms/inbound` |

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

## Tool 1: Get Current Date

**Purpose:** Call this tool FIRST to get the current server date. This prevents date confusion (e.g., AI thinking it's October 2023).

**URL:** `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/get-current-date`  
**Method:** POST  
**Content-Type:** application/json

### Request Body
```json
{}
```
*(No parameters required)*

### Headers
```
Content-Type: application/json
x-vapi-secret: service-hub-258
```

### Response Example
```json
{
  "result": "success",
  "today": {
    "date": "2025-12-18",
    "formatted": "Thursday, December 18, 2025",
    "day_of_week": "Thursday"
  },
  "tomorrow": {
    "date": "2025-12-19",
    "formatted": "Friday, December 19, 2025",
    "day_of_week": "Friday"
  },
  "instructions": "Today is Thursday, December 18, 2025. Tomorrow is Friday, December 19, 2025. Use the 'date' values (YYYY-MM-DD format) when calling check-availability."
}
```

### Vapi Tool Definition
```json
{
  "type": "function",
  "function": {
    "name": "get-current-date",
    "description": "Get the current server date. Call this tool FIRST before checking availability to know what today's date is. This prevents date confusion.",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  },
  "server": {
    "url": "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/get-current-date",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 2: Create Lead

**Purpose:** Create a new lead and customer record when a caller provides their information.

**URL:** `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/create-lead`  
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
    "url": "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/create-lead",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 3: Check Availability

**Purpose:** Check available appointment slots for a given date.

**URL:** `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/check-availability`  
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
    "url": "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/check-availability",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 4: Book Job

**Purpose:** Book a service appointment after the customer selects a time slot.

**URL:** `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/book-job`  
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
    "url": "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/book-job",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 5: Send SMS

**Purpose:** Send an SMS message to a customer (optional, for custom messages).

**URL:** `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/send-sms`  
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
    "url": "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/send-sms",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "x-vapi-secret": "service-hub-258"
    }
  }
}
```

---

## Tool 6: Log Call Summary

**Purpose:** Log a summary of the call for record-keeping (typically called at end of call).

**URL:** `https://service-hub-261.preview.emergentagent.com/api/v1/vapi/call-summary`  
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
    "url": "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/call-summary",
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

**URL:** `https://service-hub-261.preview.emergentagent.com/api/v1/sms/inbound`  
**Method:** POST  
**Content-Type:** application/x-www-form-urlencoded (Twilio's default)

### Twilio Console Configuration

1. Go to **Twilio Console** → **Phone Numbers** → **Manage** → **Active Numbers**
2. Click on your phone number (`+18777804239`)
3. Scroll to **Messaging Configuration**
4. Under **A MESSAGE COMES IN**, set:
   - **Webhook URL:** `https://service-hub-261.preview.emergentagent.com/api/v1/sms/inbound`
   - **HTTP Method:** POST

---

## Recommended Vapi System Prompt

Add this to your Vapi assistant's system prompt to ensure correct date handling:

```
## CRITICAL DATE INSTRUCTIONS
Before checking availability, you MUST know today's date. If you're unsure, call the get-current-date tool first.

When a customer says "tomorrow", "next Monday", or any relative date:
1. First determine today's actual date using get-current-date if needed
2. Calculate the correct YYYY-MM-DD date
3. Pass that date to check-availability

Example: If today is December 18, 2025 and customer says "tomorrow", pass "2025-12-19" to check-availability.

## WORKFLOW
1. Greet the customer and ask how you can help
2. Collect: name, phone, address, issue description, urgency
3. Call create-lead with all collected information
4. Ask what date works for them
5. Call get-current-date if you need to know today's date
6. Call check-availability with the requested date (YYYY-MM-DD format)
7. Present available slots to customer
8. Once they choose, call book-job with all required IDs
9. Confirm the booking and ask if there's anything else
10. Call log-call-summary before ending

## TENANT
Always use tenant_slug: "radiance-hvac" for all tool calls.
```

---

## Testing the Tools

You can test each tool using curl:

```bash
# Test get-current-date
curl -X POST "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/get-current-date" \
  -H "Content-Type: application/json" \
  -H "x-vapi-secret: service-hub-258"

# Test check-availability
curl -X POST "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/check-availability" \
  -H "Content-Type: application/json" \
  -H "x-vapi-secret: service-hub-258" \
  -d '{"tenant_slug": "radiance-hvac", "date": "tomorrow"}'

# Test create-lead
curl -X POST "https://service-hub-261.preview.emergentagent.com/api/v1/vapi/create-lead" \
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
```
