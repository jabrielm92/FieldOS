"""Centralized environment configuration for FieldOS"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
MONGO_URL: str = os.environ['MONGO_URL']
DB_NAME: str = os.environ['DB_NAME']

# JWT
JWT_SECRET: str = os.environ.get('JWT_SECRET', 'default-secret-change-me')
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRATION_HOURS: int = 24

# External services
VAPI_API_KEY: str = os.environ.get('VAPI_API_KEY', '')
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
CORS_ORIGINS: list[str] = os.environ.get('CORS_ORIGINS', '*').split(',')

# Redis (Phase 1 addition)
REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
