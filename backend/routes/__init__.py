# Routes package
from .admin import router as admin_router
from .auth import router as auth_router
from .customers import router as customers_router
from .jobs import router as jobs_router
from .invoices import router as invoices_router
from .voice import router as voice_router

__all__ = ['admin_router', 'auth_router', 'customers_router', 'jobs_router', 'invoices_router', 'voice_router']
