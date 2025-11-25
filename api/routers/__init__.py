"""
Роутеры API
"""
from .auth_router import router as auth_router
from .admin_router import router as admin_router
from .processing_router import router as processing_router

__all__ = ["auth_router", "admin_router", "processing_router"]

