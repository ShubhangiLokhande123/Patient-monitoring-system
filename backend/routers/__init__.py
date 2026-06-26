"""
Routers package - FastAPI route handlers.
"""

from routers.chat_router import router as chat_router
from routers.patients_router import router as patients_router
from routers.alerts_router import router as alerts_router

__all__ = ["chat_router", "patients_router", "alerts_router"]
