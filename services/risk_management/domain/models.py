"""Risk Management - ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TimestampMixin


class RiskProfile(TimestampMixin, Base):
    __tablename__ = "risk_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    max_position_size_pct: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, default=0.02
    )
    daily_loss_limit_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.05)
    weekly_loss_limit_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.06)
    monthly_loss_limit_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.10)
    max_drawdown_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.15)
    risk_per_trade_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.01)
    max_open_positions: Mapped[int] = mapped_column(nullable=False, default=10)
    kelly_fraction: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.25)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
