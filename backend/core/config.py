"""Centralized environment configuration for FieldOS"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Runtime environment
ENVIRONMENT: str = os.environ.get('ENVIRONMENT', 'development').lower()

# MongoDB
MONGO_URL: str = os.environ['MONGO_URL']
DB_NAME: str = os.environ['DB_NAME']

# JWT (required)
JWT_SECRET: str = os.environ.get('JWT_SECRET', '')
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRATION_HOURS: int = 24

# External services
OPENAI_API_KEY: str = os.environ.get('OPENAI_API_KEY', '')
TWILIO_ACCOUNT_SID: str = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN: str = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_MESSAGING_SERVICE_SID: str = os.environ.get('TWILIO_MESSAGING_SERVICE_SID', '')
STRIPE_SECRET_KEY: str = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET: str = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
RESEND_API_KEY: str = os.environ.get('RESEND_API_KEY', '')
ELEVENLABS_API_KEY: str = os.environ.get('ELEVENLABS_API_KEY', '')

# App
FRONTEND_URL: str = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
def _default_cors() -> str:
    return 'http://localhost:3000,http://localhost:5173,http://localhost'

CORS_ORIGINS: list[str] = [origin.strip() for origin in os.environ.get('CORS_ORIGINS', _default_cors()).split(',') if origin.strip()]

# Redis
REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


def is_production() -> bool:
    return ENVIRONMENT in {"prod", "production"}


def validate_security_settings() -> None:
    """Fail fast for insecure runtime defaults."""
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be set")

    if JWT_SECRET == 'default-secret-change-me' or len(JWT_SECRET) < 16:
        raise RuntimeError("JWT_SECRET is too weak; set a stronger secret")

    if not CORS_ORIGINS or '*' in CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS must be explicit and cannot include '*'")

    if is_production() and len(JWT_SECRET) < 32:
        raise RuntimeError("In production, JWT_SECRET must be at least 32 chars long")
