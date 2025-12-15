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
      "type": "boolean"
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
    }
  }
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
      "type": "string"
    },
    "windows": {
      "type": "array",
      "description": "Available time windows",
      "items": {
        "type": "object",
        "properties": {
          "start": {"type": "string"},
          "end": {"type": "string"},
          "label": {"type": "string"},
          "available": {"type": "boolean"}
        }
      }
    },
    "message": {
      "type": "string"
    }
  }
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
      "type": "boolean"
    },
    "job_id": {
      "type": "string"
    },
    "message": {
      "type": "string"
    }
  }
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
    "error": {
      "type": "string"
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
| create_lead | https://service-hub-258.preview.emergentagent.com/api/v1/vapi/create-lead |
| check_availability | https://service-hub-258.preview.emergentagent.com/api/v1/vapi/check-availability |
| book_job | https://service-hub-258.preview.emergentagent.com/api/v1/vapi/book-job |
| send_followup_sms | https://service-hub-258.preview.emergentagent.com/api/v1/vapi/send-sms |
| log_call_summary | https://service-hub-258.preview.emergentagent.com/api/v1/vapi/call-summary |

All tools use:
- **Method:** POST
- **Header:** Content-Type: application/json
- **No Authentication Required** (handled by tenant_slug)
