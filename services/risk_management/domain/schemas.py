"""Risk Management - Pydantic schemas."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import Field

from shared.schemas.base import BaseSchema


class RiskSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PositionSizeMethod(StrEnum):
    FIXED_FRACTIONAL = "fixed_fractional"
    KELLY = "kelly"
    FIXED_UNITS = "fixed_units"
    PERCENT_EQUITY = "percent_equity"


class PositionSizeRequest(BaseSchema):
    ticker: str
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    account_equity: float = Field(..., gt=0)
    risk_per_trade_pct: float = Field(default=0.01, gt=0, le=0.1)
    method: PositionSizeMethod = PositionSizeMethod.FIXED_FRACTIONAL
    # Kelly-specific
    win_rate: float | None = Field(default=None, ge=0, le=1)
    avg_win_loss_ratio: float | None = Field(default=None, gt=0)
    kelly_fraction: float = Field(default=0.25, gt=0, le=1)


class PositionSizeResponse(BaseSchema):
    ticker: str
    method: str
    entry_price: float
    stop_loss: float
    quantity: float
    risk_amount: float
    risk_pct: float
    position_value: float
    position_pct: float


class RiskCheckRequest(BaseSchema):
    account_equity: float
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    current_drawdown_pct: float = 0.0
    open_positions: int = 0
    proposed_position_pct: float = 0.0


class RiskCheckResponse(BaseSchema):
    approved: bool
    reasons: list[str] = []
    warnings: list[str] = []


class DrawdownStatus(BaseSchema):
    current_equity: float
    peak_equity: float
    current_drawdown_pct: float
    max_drawdown_pct: float
    is_circuit_breaker_active: bool
    daily_loss_pct: float
    daily_loss_limit_pct: float


class RiskProfileCreate(BaseSchema):
    name: str
    description: str | None = None
    max_position_size_pct: float = Field(default=0.02, gt=0, le=0.5)
    daily_loss_limit_pct: float = Field(default=0.05, gt=0, le=0.5)
    weekly_loss_limit_pct: float = Field(default=0.06, gt=0, le=0.5)
    monthly_loss_limit_pct: float = Field(default=0.10, gt=0, le=0.5)
    max_drawdown_pct: float = Field(default=0.15, gt=0, le=0.8)
    risk_per_trade_pct: float = Field(default=0.01, gt=0, le=0.1)
    max_open_positions: int = Field(default=10, gt=0, le=100)
    kelly_fraction: float = Field(default=0.25, gt=0, le=1)
    is_active: bool = False


class RiskProfileResponse(RiskProfileCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
