"""
Security hardening for FieldOS:
  - Rate limiting via slowapi
  - Audit logging (who did what to which record)
  - TOTP two-factor authentication helpers
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import pyotp
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.database import db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)
"""
Usage in routes:
    from core.security import limiter
    from slowapi.errors import RateLimitExceeded

    @router.post("/auth/login")
    @limiter.limit("10/minute")
    async def login(request: Request, ...):
        ...

Register on the FastAPI app in server.py:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
"""


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------

async def audit_log(
    action: str,
    resource_type: str,
    resource_id: str,
    user_id: str,
    tenant_id: Optional[str],
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    metadata: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    """
    Record an immutable audit log entry.

    Examples:
        await audit_log("CREATE", "job", job_id, user["id"], tenant_id, after=job_dict)
        await audit_log("UPDATE", "tenant", tenant_id, user["id"], tenant_id, before=old, after=new)
        await audit_log("DELETE", "customer", customer_id, user["id"], tenant_id, before=customer)
    """
    ip_address = None
    if request:
        forwarded = request.headers.get("x-forwarded-for")
        ip_address = forwarded.split(",")[0].strip() if forwarded else request.client.host

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,           # CREATE / READ / UPDATE / DELETE / LOGIN / LOGOUT
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "ip_address": ip_address,
        "before": before,
        "after": after,
        "metadata": metadata or {},
    }

    try:
        await db.audit_logs.insert_one(entry)
    except Exception as exc:
        # Audit logging must never break the main request
        logger.error(f"Audit log write failed: {exc}")


# ---------------------------------------------------------------------------
# TOTP Two-Factor Authentication
# ---------------------------------------------------------------------------

def generate_totp_secret() -> str:
    """Generate a new TOTP secret for a user."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "FieldOS") -> str:
    """
    Return the otpauth:// URI for QR code generation.
    Display this URI as a QR code in the 2FA setup flow.
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=issuer,
    )


def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code against the stored secret."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # ±30 seconds tolerance
