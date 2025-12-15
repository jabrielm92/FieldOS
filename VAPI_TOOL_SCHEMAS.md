# VAPI TOOL JSON SCHEMAS - Copy/Paste Ready

## Tool 1: create_lead

### Request Body (JSON Schema)
```json
{
  "type": "object",
  "properties": {
    "tenant_slug": {
      "type": "string",
      "description": "The tenant identifier",
      "default": "radiance-hvac"
    },
    "urgency": {
      "type": "string",
      "enum": ["ROUTINE", "URGENT", "EMERGENCY"],
      "description": "How urgent is the service request"
    },
    "caller_number": {
      "type": "string",
      "description": "Customer's phone number in +1XXXXXXXXXX format"
    },
    "captured_name": {
      "type": "string",
      "description": "Customer's full name"
    },
    "captured_email": {
      "type": "string",
      "description": "Customer's email address (optional)"
    },
    "captured_address": {
      "type": "string",
      "description": "Full service address like: 123 Main St, Chicago, IL 60601"
    },
    "issue_description": {
      "type": "string",
      "description": "Description of the HVAC issue"
    }
  },
  "required": ["tenant_slug", "urgency", "caller_number", "captured_name", "captured_address", "issue_description"]
}
```

### Response Body
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "Whether the lead was created successfully"
    },
    "lead_id": {
      "type": "string",
      "description": "Lead ID - SAVE THIS for book_job and log_call_summary"
    },
    "customer_id": {
      "type": "string",
      "description": "Customer ID - SAVE THIS for book_job"
    },
    "property_id": {
      "type": "string",
      "description": "Property ID - SAVE THIS for book_job"
    },
    "conversation_id": {
      "type": "string",
      "description": "Conversation ID"
    },
    "message": {
      "type": "string",
      "description": "Human-readable status message explaining what was created and what to do next"
    }
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "lead_id": "abc123-...",
  "customer_id": "cust456-...",
  "property_id": "prop789-...",
  "conversation_id": "conv012-...",
  "message": "Lead created successfully for John. Customer ID is cust456-..., property ID is prop789-..., and lead ID is abc123-.... You can now check availability and book a job using these IDs."
}
```

---

## Tool 2: check_availability

### Request Body (JSON Schema)
```json
{
  "type": "object",
  "properties": {
    "tenant_slug": {
      "type": "string",
      "description": "The tenant identifier",
      "default": "radiance-hvac"
    },
    "date": {
      "type": "string",
      "description": "Date to check availability, format: YYYY-MM-DD (e.g., 2025-12-16)"
    },
    "job_type": {
      "type": "string",
      "enum": ["DIAGNOSTIC", "REPAIR", "INSTALL", "MAINTENANCE", "INSPECTION"],
      "description": "Type of service needed",
      "default": "DIAGNOSTIC"
    }
  },
  "required": ["tenant_slug", "date"]
}
```

### Response Body
```json
{
  "type": "object",
  "properties": {
    "date": {
      "type": "string",
      "description": "The date that was checked"
    },
    "has_availability": {
      "type": "boolean",
      "description": "Whether there are any available slots"
    },
    "windows": {
      "type": "array",
      "description": "Available time windows",
      "items": {
        "type": "object",
        "properties": {
          "start": {"type": "string", "description": "Start time (24hr format, e.g., 08:00)"},
          "end": {"type": "string", "description": "End time (24hr format, e.g., 12:00)"},
          "label": {"type": "string", "description": "Human-readable label like 'Morning (8am-12pm)'"},
          "available": {"type": "boolean"}
        }
      }
    },
    "message": {
      "type": "string",
      "description": "Human-readable message to tell the customer about available slots"
    },
    "next_step": {
      "type": "string",
      "description": "Instructions for what to do next"
    }
  }
}
```

**Example Response (slots available):**
```json
{
  "date": "2025-12-16",
  "has_availability": true,
  "windows": [
    {"date": "2025-12-16", "start": "08:00", "end": "12:00", "label": "Morning (8am-12pm)", "available": true},
    {"date": "2025-12-16", "start": "12:00", "end": "17:00", "label": "Afternoon (12pm-5pm)", "available": true}
  ],
  "message": "For 2025-12-16, the following time slots are available: Morning (8am-12pm), Afternoon (12pm-5pm). Ask the customer which time slot works best for them.",
  "next_step": "Ask the customer which time slot they prefer, then call the book-job tool with their selection."
}
```

**Example Response (no slots):**
```json
{
  "date": "2025-12-16",
  "has_availability": false,
  "windows": [],
  "message": "Unfortunately, there are no available time slots for 2025-12-16. Please ask the customer for an alternative date.",
  "next_step": "Ask the customer which time slot they prefer, then call the book-job tool with their selection."
}
```

---

## Tool 3: book_job

### Request Body (JSON Schema)
```json
{
  "type": "object",
  "properties": {
    "tenant_slug": {
      "type": "string",
      "description": "The tenant identifier",
      "default": "radiance-hvac"
    },
    "lead_id": {
      "type": "string",
      "description": "The lead_id returned from create_lead"
    },
    "customer_id": {
      "type": "string",
      "description": "The customer_id returned from create_lead"
    },
    "property_id": {
      "type": "string",
      "description": "The property_id returned from create_lead"
    },
    "job_type": {
      "type": "string",
      "enum": ["DIAGNOSTIC", "REPAIR", "INSTALL", "MAINTENANCE", "INSPECTION"],
      "description": "Type of service appointment"
    },
    "window_start": {
      "type": "string",
      "description": "Appointment start time in ISO 8601 format (e.g., 2025-12-16T08:00:00-06:00)"
    },
    "window_end": {
      "type": "string",
      "description": "Appointment end time in ISO 8601 format (e.g., 2025-12-16T12:00:00-06:00)"
    }
  },
  "required": ["tenant_slug", "lead_id", "customer_id", "property_id", "job_type", "window_start", "window_end"]
}
```

### Response Body
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "Whether the job was booked successfully"
    },
    "job_id": {
      "type": "string",
      "description": "The unique job ID"
    },
    "message": {
      "type": "string",
      "description": "Human-readable confirmation message to tell the customer"
    },
    "confirmation": {
      "type": "object",
      "properties": {
        "date": {"type": "string", "description": "Formatted date like 'Monday, December 16'"},
        "time_window": {"type": "string", "description": "Formatted time like '8:00 AM to 12:00 PM'"},
        "customer_name": {"type": "string"}
      }
    },
    "next_step": {
      "type": "string",
      "description": "What to tell the customer after booking"
    }
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "job_id": "job123-...",
  "message": "Great news! The appointment has been successfully booked for Monday, December 16 between 08:00 AM to 12:00 PM. The customer will receive a confirmation text message. Job ID is job123-....",
  "confirmation": {
    "date": "Monday, December 16",
    "time_window": "08:00 AM to 12:00 PM",
    "customer_name": "John"
  },
  "next_step": "Confirm with the customer that their appointment is booked and let them know they will receive a text confirmation."
}
```

---

## Tool 4: send_followup_sms

### Request Body (JSON Schema)
```json
{
  "type": "object",
  "properties": {
    "tenant_slug": {
      "type": "string",
      "description": "The tenant identifier",
      "default": "radiance-hvac"
    },
    "to_phone": {
      "type": "string",
      "description": "Customer's phone number"
    },
    "message": {
      "type": "string",
      "description": "The SMS message to send (keep under 160 characters)"
    }
  },
  "required": ["tenant_slug", "to_phone", "message"]
}
```

### Response Body
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    },
    "message_id": {
      "type": "string"
    },
    "message": {
      "type": "string",
      "description": "Status message indicating success or failure"
    },
    "error": {
      "type": "string",
      "description": "Error message if send failed"
    }
  }
}
```

---

## Tool 5: log_call_summary

### Request Body (JSON Schema)
```json
{
  "type": "object",
  "properties": {
    "tenant_slug": {
      "type": "string",
      "description": "The tenant identifier",
      "default": "radiance-hvac"
    },
    "lead_id": {
      "type": "string",
      "description": "The lead_id from create_lead"
    },
    "summary": {
      "type": "string",
      "description": "Brief summary: customer name, issue, what happened (booked/not booked), any notes"
    },
    "vapi_session_id": {
      "type": "string",
      "description": "The Vapi call session ID"
    }
  },
  "required": ["tenant_slug", "lead_id", "summary"]
}
```

### Response Body
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    },
    "message_id": {
      "type": "string"
    }
  }
}
```

---

## TOOL URLS QUICK REFERENCE

| Tool | URL |
|------|-----|
| create_lead | https://YOUR_DEPLOYMENT_URL/api/v1/vapi/create-lead |
| check_availability | https://YOUR_DEPLOYMENT_URL/api/v1/vapi/check-availability |
| book_job | https://YOUR_DEPLOYMENT_URL/api/v1/vapi/book-job |
| send_followup_sms | https://YOUR_DEPLOYMENT_URL/api/v1/vapi/send-sms |
| log_call_summary | https://YOUR_DEPLOYMENT_URL/api/v1/vapi/call-summary |

All tools use:
- **Method:** POST
- **Header:** Content-Type: application/json
- **No Authentication Required** (handled by tenant_slug)

---

## IMPORTANT NOTES FOR VAPI ASSISTANT

1. **Always save the IDs** returned from `create_lead`:
   - `lead_id` - needed for `book_job` and `log_call_summary`
   - `customer_id` - needed for `book_job`
   - `property_id` - needed for `book_job`

2. **Date format for check_availability**: Use `YYYY-MM-DD` format (e.g., `2025-12-16`)

3. **DateTime format for book_job**: Use ISO 8601 with timezone (e.g., `2025-12-16T08:00:00-06:00`)

4. **Read the `message` field** in responses - it tells you exactly what to say to the customer.

5. **Read the `next_step` field** in responses - it tells you what action to take next.

6. **Time windows**:
   - Morning: 08:00 to 12:00 (8am-12pm)
   - Afternoon: 12:00 to 17:00 (12pm-5pm)
