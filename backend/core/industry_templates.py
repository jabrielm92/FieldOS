"""
FieldOS Industry Template System

Each template defines the full configuration for a vertical, enabling the
platform to serve any service business with appropriate terminology,
workflows, and AI scripts — without hard-coding field service concepts.

Structure:
    - name: Human-readable vertical name
    - terminology: Maps generic concepts to industry-specific language
    - service_types: The equivalent of "job types" for this vertical
    - urgency_levels: How urgency is described in this vertical
    - default_greeting: AI receptionist opening line
    - ai_intake_questions: Questions the AI asks to qualify the caller
    - booking_noun: What a "job" is called (appointment, visit, session...)
    - staff_noun: What a "technician" is called (agent, provider, stylist...)
    - features: Which optional feature modules are relevant for this vertical
    - pricing_hints: Default base prices for service types
"""

INDUSTRY_TEMPLATES: dict = {

    # ----------------------------------------------------------------
    # FIELD SERVICE (original verticals)
    # ----------------------------------------------------------------

    "hvac": {
        "name": "HVAC",
        "category": "field_service",
        "terminology": {
            "job": "appointment",
            "jobs": "appointments",
            "technician": "technician",
            "technicians": "technicians",
            "dispatch": "dispatch",
            "property": "property",
            "service_request": "service request",
        },
        "service_types": [
            "AC Repair", "Heating Repair", "AC Installation",
            "Furnace Installation", "Maintenance", "Duct Cleaning",
            "Thermostat Install", "Heat Pump Service", "Air Quality",
        ],
        "urgency_levels": {
            "EMERGENCY": "No heat/no cooling — emergency",
            "URGENT": "System degraded — urgent",
            "ROUTINE": "Scheduled maintenance",
        },
        "booking_noun": "appointment",
        "staff_noun": "technician",
        "default_greeting": "Thank you for calling. How can I help with your heating or cooling today?",
        "ai_intake_questions": [
            "What seems to be the issue with your system?",
            "How old is your unit approximately?",
            "Is this a heating or cooling problem?",
            "Have you noticed any unusual sounds or smells?",
        ],
        "features": {
            "dispatch_board": True,
            "on_my_way": True,
            "maintenance_plans": True,
            "equipment_tracking": True,
            "parts_inventory": True,
            "review_requests": True,
        },
        "pricing_hints": {
            "DIAGNOSTIC": 89.00,
            "REPAIR": 250.00,
            "INSTALLATION": 1500.00,
            "MAINTENANCE": 149.00,
            "INSPECTION": 75.00,
        },
    },

    "plumbing": {
        "name": "Plumbing",
        "category": "field_service",
        "terminology": {
            "job": "service call",
            "jobs": "service calls",
            "technician": "plumber",
            "technicians": "plumbers",
            "dispatch": "dispatch",
            "property": "property",
            "service_request": "service request",
        },
        "service_types": [
            "Leak Repair", "Drain Cleaning", "Water Heater",
            "Toilet Repair", "Faucet Install", "Pipe Repair",
            "Sewer Line", "Water Softener", "Backflow Testing",
        ],
        "urgency_levels": {
            "EMERGENCY": "Active leak / flooding",
            "URGENT": "No hot water / slow drain",
            "ROUTINE": "Scheduled service",
        },
        "booking_noun": "service call",
        "staff_noun": "plumber",
        "default_greeting": "Thank you for calling. What plumbing issue can I help you with today?",
        "ai_intake_questions": [
            "Can you describe the issue you're experiencing?",
            "Is there any active water leaking right now?",
            "Which part of the home is affected?",
        ],
        "features": {
            "dispatch_board": True,
            "on_my_way": True,
            "maintenance_plans": True,
            "equipment_tracking": True,
            "parts_inventory": True,
            "review_requests": True,
        },
        "pricing_hints": {
            "DIAGNOSTIC": 89.00,
            "REPAIR": 200.00,
            "INSTALLATION": 800.00,
            "MAINTENANCE": 125.00,
            "INSPECTION": 75.00,
        },
    },

    "electrical": {
        "name": "Electrical",
        "category": "field_service",
        "terminology": {
            "job": "service call",
            "jobs": "service calls",
            "technician": "electrician",
            "technicians": "electricians",
            "dispatch": "dispatch",
            "property": "property",
            "service_request": "service request",
        },
        "service_types": [
            "Outlet Repair", "Panel Upgrade", "Wiring",
            "Lighting Install", "Generator", "EV Charger",
            "Ceiling Fan", "Smoke Detector", "Surge Protection",
        ],
        "urgency_levels": {
            "EMERGENCY": "Sparks / burning smell / no power",
            "URGENT": "Partial power outage / tripped breakers",
            "ROUTINE": "Scheduled service",
        },
        "booking_noun": "service call",
        "staff_noun": "electrician",
        "default_greeting": "Thank you for calling. What electrical issue can I help you with?",
        "ai_intake_questions": [
            "What electrical issue are you experiencing?",
            "Are you seeing any sparks or smelling burning?",
            "Is this affecting your whole home or just certain areas?",
        ],
        "features": {
            "dispatch_board": True,
            "on_my_way": True,
            "maintenance_plans": False,
            "equipment_tracking": True,
            "parts_inventory": True,
            "review_requests": True,
        },
        "pricing_hints": {
            "DIAGNOSTIC": 95.00,
            "REPAIR": 300.00,
            "INSTALLATION": 1200.00,
            "INSPECTION": 125.00,
        },
    },

    "landscaping": {
        "name": "Landscaping",
        "category": "field_service",
        "terminology": {
            "job": "service visit",
            "jobs": "service visits",
            "technician": "crew member",
            "technicians": "crew members",
            "dispatch": "scheduling",
            "property": "property",
            "service_request": "service request",
        },
        "service_types": [
            "Lawn Care", "Tree Service", "Irrigation",
            "Hardscape", "Design", "Seasonal Cleanup",
            "Fertilization", "Pest Control", "Mulching",
        ],
        "urgency_levels": {
            "EMERGENCY": "Storm damage / hazard tree",
            "URGENT": "Before event / deadline",
            "ROUTINE": "Scheduled maintenance",
        },
        "booking_noun": "service visit",
        "staff_noun": "crew member",
        "default_greeting": "Thank you for calling. How can I help with your landscaping needs?",
        "ai_intake_questions": [
            "What type of landscaping service are you looking for?",
            "How large is your property?",
            "Is this a one-time or recurring service?",
        ],
        "features": {
            "dispatch_board": True,
            "on_my_way": True,
            "maintenance_plans": True,
            "equipment_tracking": False,
            "parts_inventory": False,
            "review_requests": True,
        },
        "pricing_hints": {
            "MAINTENANCE": 75.00,
            "REPAIR": 150.00,
            "INSTALLATION": 500.00,
            "INSPECTION": 50.00,
        },
    },

    "cleaning": {
        "name": "Cleaning",
        "category": "field_service",
        "terminology": {
            "job": "cleaning appointment",
            "jobs": "cleaning appointments",
            "technician": "cleaner",
            "technicians": "cleaners",
            "dispatch": "scheduling",
            "property": "home",
            "service_request": "service request",
        },
        "service_types": [
            "Regular Cleaning", "Deep Clean", "Move-In/Out",
            "Post-Construction", "Carpet Cleaning", "Window Cleaning",
            "Office Cleaning", "Airbnb Turnover",
        ],
        "urgency_levels": {
            "EMERGENCY": "Same day needed",
            "URGENT": "Next day / ASAP",
            "ROUTINE": "Scheduled recurring",
        },
        "booking_noun": "appointment",
        "staff_noun": "cleaner",
        "default_greeting": "Thank you for calling. What type of cleaning service are you looking for?",
        "ai_intake_questions": [
            "What type of cleaning are you looking for?",
            "How many bedrooms and bathrooms does your home have?",
            "Is this a one-time or recurring service?",
        ],
        "features": {
            "dispatch_board": True,
            "on_my_way": True,
            "maintenance_plans": True,
            "equipment_tracking": False,
            "parts_inventory": False,
            "review_requests": True,
        },
        "pricing_hints": {
            "MAINTENANCE": 120.00,
            "DIAGNOSTIC": 0.00,
            "INSPECTION": 0.00,
            "REPAIR": 0.00,
            "INSTALLATION": 0.00,
        },
    },

    # ----------------------------------------------------------------
    # EXPANSION VERTICALS (Phase 5 targets)
    # ----------------------------------------------------------------

    "auto_repair": {
        "name": "Auto Repair",
        "category": "automotive",
        "terminology": {
            "job": "repair order",
            "jobs": "repair orders",
            "technician": "mechanic",
            "technicians": "mechanics",
            "dispatch": "shop queue",
            "property": "vehicle",
            "service_request": "repair request",
        },
        "service_types": [
            "Oil Change", "Brake Service", "Tire Rotation",
            "Engine Diagnostics", "Transmission", "AC Service",
            "Battery Replacement", "Alignment", "Suspension",
        ],
        "urgency_levels": {
            "EMERGENCY": "Vehicle not drivable",
            "URGENT": "Safety concern",
            "ROUTINE": "Scheduled service",
        },
        "booking_noun": "appointment",
        "staff_noun": "mechanic",
        "default_greeting": "Thank you for calling. What can we help you with on your vehicle today?",
        "ai_intake_questions": [
            "What is the year, make, and model of your vehicle?",
            "What issue are you experiencing?",
            "Approximately how many miles are on the vehicle?",
        ],
        "features": {
            "dispatch_board": True,
            "on_my_way": False,
            "maintenance_plans": True,
            "equipment_tracking": True,
            "parts_inventory": True,
            "review_requests": True,
        },
        "pricing_hints": {
            "DIAGNOSTIC": 99.00,
            "REPAIR": 300.00,
            "MAINTENANCE": 89.00,
            "INSPECTION": 49.00,
        },
    },

    "med_spa": {
        "name": "Med Spa / Aesthetics",
        "category": "health_beauty",
        "terminology": {
            "job": "appointment",
            "jobs": "appointments",
            "technician": "provider",
            "technicians": "providers",
            "dispatch": "scheduling",
            "property": "client",
            "service_request": "consultation request",
        },
        "service_types": [
            "Botox / Filler", "Laser Treatment", "Chemical Peel",
            "Microneedling", "Body Contouring", "IV Therapy",
            "Consultation", "Membership Intake", "Follow-up",
        ],
        "urgency_levels": {
            "EMERGENCY": "Adverse reaction",
            "URGENT": "Pre-event / deadline",
            "ROUTINE": "Scheduled appointment",
        },
        "booking_noun": "appointment",
        "staff_noun": "provider",
        "default_greeting": "Thank you for calling. How can I help you schedule a treatment today?",
        "ai_intake_questions": [
            "What treatment are you interested in?",
            "Have you had this treatment before?",
            "Do you have any allergies or sensitivities we should know about?",
        ],
        "features": {
            "dispatch_board": False,
            "on_my_way": False,
            "maintenance_plans": True,
            "equipment_tracking": False,
            "parts_inventory": False,
            "review_requests": True,
        },
        "pricing_hints": {
            "DIAGNOSTIC": 0.00,
            "REPAIR": 0.00,
            "MAINTENANCE": 200.00,
            "INSPECTION": 75.00,
            "INSTALLATION": 0.00,
        },
    },

    "home_care": {
        "name": "Home Care",
        "category": "care_services",
        "terminology": {
            "job": "visit",
            "jobs": "visits",
            "technician": "caregiver",
            "technicians": "caregivers",
            "dispatch": "scheduling",
            "property": "client home",
            "service_request": "care request",
        },
        "service_types": [
            "Companion Care", "Personal Care", "Dementia Care",
            "Post-Surgery Care", "Respite Care", "Overnight Care",
            "Transportation", "Medication Reminders",
        ],
        "urgency_levels": {
            "EMERGENCY": "Medical emergency",
            "URGENT": "Immediate care needed",
            "ROUTINE": "Scheduled visit",
        },
        "booking_noun": "visit",
        "staff_noun": "caregiver",
        "default_greeting": "Thank you for calling. How can I help you with care services today?",
        "ai_intake_questions": [
            "What type of care are you looking for?",
            "Who is the care for — yourself or a family member?",
            "How many hours per week are you looking for?",
        ],
        "features": {
            "dispatch_board": True,
            "on_my_way": True,
            "maintenance_plans": True,
            "equipment_tracking": False,
            "parts_inventory": False,
            "review_requests": True,
        },
        "pricing_hints": {
            "MAINTENANCE": 25.00,  # per hour
            "DIAGNOSTIC": 0.00,
            "INSPECTION": 0.00,
            "REPAIR": 0.00,
            "INSTALLATION": 0.00,
        },
    },

    "consulting": {
        "name": "Consulting / Professional Services",
        "category": "professional_services",
        "terminology": {
            "job": "engagement",
            "jobs": "engagements",
            "technician": "consultant",
            "technicians": "consultants",
            "dispatch": "scheduling",
            "property": "client",
            "service_request": "inquiry",
        },
        "service_types": [
            "Discovery Call", "Strategy Session", "Implementation",
            "Audit", "Training", "Ongoing Retainer", "Workshop",
        ],
        "urgency_levels": {
            "EMERGENCY": "Critical blocker",
            "URGENT": "Time-sensitive",
            "ROUTINE": "Scheduled",
        },
        "booking_noun": "session",
        "staff_noun": "consultant",
        "default_greeting": "Thank you for calling. How can I help you today?",
        "ai_intake_questions": [
            "What type of help are you looking for?",
            "Can you tell me a little about your business?",
            "What is your timeline for getting started?",
        ],
        "features": {
            "dispatch_board": False,
            "on_my_way": False,
            "maintenance_plans": True,
            "equipment_tracking": False,
            "parts_inventory": False,
            "review_requests": True,
        },
        "pricing_hints": {
            "DIAGNOSTIC": 0.00,
            "REPAIR": 0.00,
            "MAINTENANCE": 500.00,
            "INSPECTION": 200.00,
            "INSTALLATION": 2500.00,
        },
    },

    "general": {
        "name": "General / Other",
        "category": "general",
        "terminology": {
            "job": "appointment",
            "jobs": "appointments",
            "technician": "staff member",
            "technicians": "staff members",
            "dispatch": "scheduling",
            "property": "location",
            "service_request": "service request",
        },
        "service_types": [
            "Consultation", "Service", "Repair",
            "Installation", "Maintenance", "Inspection",
        ],
        "urgency_levels": {
            "EMERGENCY": "Emergency",
            "URGENT": "Urgent",
            "ROUTINE": "Routine",
        },
        "booking_noun": "appointment",
        "staff_noun": "staff member",
        "default_greeting": "Thank you for calling. How can I help you today?",
        "ai_intake_questions": [
            "What can I help you with today?",
            "Can you describe what you need?",
        ],
        "features": {
            "dispatch_board": True,
            "on_my_way": True,
            "maintenance_plans": True,
            "equipment_tracking": False,
            "parts_inventory": False,
            "review_requests": True,
        },
        "pricing_hints": {
            "DIAGNOSTIC": 89.00,
            "REPAIR": 200.00,
            "INSTALLATION": 500.00,
            "MAINTENANCE": 125.00,
            "INSPECTION": 75.00,
        },
    },
}


def get_template(industry: str) -> dict | None:
    """Return a template by industry key, case-insensitive."""
    return INDUSTRY_TEMPLATES.get(industry.lower())


def list_templates() -> dict:
    """Return all templates with metadata only (no AI prompts) for dropdowns."""
    return {
        key: {
            "name": tpl["name"],
            "category": tpl["category"],
            "booking_noun": tpl["booking_noun"],
            "staff_noun": tpl["staff_noun"],
            "service_types": tpl["service_types"],
        }
        for key, tpl in INDUSTRY_TEMPLATES.items()
    }
