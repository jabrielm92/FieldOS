"""Shared utility functions for FieldOS"""
from datetime import datetime


def serialize_doc(doc: dict) -> dict:
    """Serialize a single MongoDB document for JSON response"""
    if doc is None:
        return None
    result = {k: v for k, v in doc.items() if k != '_id'}
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result


def serialize_docs(docs: list) -> list:
    """Serialize a list of MongoDB documents"""
    return [serialize_doc(doc) for doc in docs]


def normalize_phone_e164(phone: str) -> str:
    """
    Normalize a phone number to E.164 format (+1XXXXXXXXXX).
    Assumes US numbers if no country code is provided.
    """
    if not phone:
        return ""
    digits = ''.join(c for c in phone if c.isdigit())
    if phone.startswith('+1') and len(digits) == 11 and digits.startswith('1'):
        return '+' + digits
    if len(digits) == 10:
        digits = '1' + digits
    elif len(digits) == 11 and digits.startswith('1'):
        pass
    else:
        return '+' + digits if digits else ""
    return '+' + digits


def calculate_quote_amount(job_type: str, urgency: str = None) -> float:
    """Calculate a quote estimate based on job type and urgency multiplier"""
    base_prices = {
        "DIAGNOSTIC": 89.00,
        "REPAIR": 250.00,
        "MAINTENANCE": 149.00,
        "INSTALL": 1500.00,
        "INSTALLATION": 1500.00,
        "INSPECTION": 75.00,
    }
    urgency_multipliers = {
        "EMERGENCY": 1.5,
        "URGENT": 1.25,
        "ROUTINE": 1.0,
    }
    base = base_prices.get(job_type, 150.00)
    multiplier = urgency_multipliers.get(urgency, 1.0)
    return round(base * multiplier, 2)
