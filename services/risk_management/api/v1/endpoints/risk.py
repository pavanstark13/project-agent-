"""Risk Management API endpoints."""

import structlog
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.risk_management.domain.schemas import (
    DrawdownStatus,
    PositionSizeRequest,
    PositionSizeResponse,
    RiskCheckRequest,
    RiskCheckResponse,
)
from services.risk_management.services.drawdown_monitor import DrawdownMonitor
from services.risk_management.services.loss_limiter import LossLimiter
from services.risk_management.services.position_sizer import PositionSizer
from shared.database import get_db
from shared.exceptions import ValidationError

router = APIRouter()
logger = structlog.get_logger(__name__)

settings = get_settings()
_position_sizer = PositionSizer()
_drawdown_monitor = DrawdownMonitor()
_loss_limiter = LossLimiter(
    daily_loss_limit_pct=settings.default_daily_loss_limit,
    weekly_loss_limit_pct=settings.default_weekly_loss_limit,
    monthly_loss_limit_pct=settings.default_monthly_loss_limit,
    max_drawdown_pct=settings.default_max_drawdown,
    max_open_positions=settings.default_max_open_positions,
    max_position_size_pct=settings.default_max_position_pct,
)


@router.post("/position-size", response_model=PositionSizeResponse)
async def calculate_position_size(request: PositionSizeRequest) -> PositionSizeResponse:
    """Calculate position size using specified method."""
    try:
        return _position_sizer.calculate(request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Position size calculation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check", response_model=RiskCheckResponse)
async def check_trade_risk(
    request: RiskCheckRequest,
    db: AsyncSession = Depends(get_db),
) -> RiskCheckResponse:
    """Check if a trade meets risk criteria."""
    return await _loss_limiter.check_trade_allowed(request, db)


@router.get("/drawdown/{equity}", response_model=DrawdownStatus)
async def get_drawdown_status(equity: float) -> DrawdownStatus:
    """Get current drawdown status for given equity level."""
    if equity <= 0:
        raise HTTPException(status_code=400, detail="Equity must be positive")
    return await _drawdown_monitor.update(equity)


@router.post("/circuit-breaker/activate")
async def activate_circuit_breaker(reason: str) -> dict:
    """Activate trading circuit breaker."""
    await _loss_limiter.activate_circuit_breaker(reason)
    return {"status": "activated", "reason": reason}


@router.post("/circuit-breaker/deactivate")
async def deactivate_circuit_breaker() -> dict:
    """Deactivate trading circuit breaker."""
    await _loss_limiter.deactivate_circuit_breaker()
    return {"status": "deactivated"}


@router.get("/circuit-breaker/status")
async def get_circuit_breaker_status() -> dict:
    """Get circuit breaker status."""
    is_active = await _loss_limiter.is_circuit_breaker_active()
    return {"is_active": is_active}
