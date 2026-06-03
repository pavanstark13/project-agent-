"""Execution Engine - API v1 router."""

from fastapi import APIRouter

from services.execution_engine.api.v1.endpoints.health import router as health_router
from services.execution_engine.api.v1.endpoints.orders import router as orders_router
from services.execution_engine.api.v1.endpoints.risk import router as risk_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(orders_router, prefix="/orders", tags=["orders"])
router.include_router(risk_router, prefix="/risk", tags=["risk"])
