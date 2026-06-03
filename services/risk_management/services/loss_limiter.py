"""Loss limiter - circuit breaker for daily and trade loss limits."""

from datetime import UTC, datetime
from typing import Any

import structlog

from services.risk_management.domain.schemas import RiskCheckRequest, RiskCheckResponse
from shared.redis_client import RedisCache

logger = structlog.get_logger(__name__)


class LossLimiter:
    """
    Enforces loss limits and acts as circuit breaker.

    Checks:
    - Daily loss limit (stop trading for the day)
    - Max drawdown limit (halt all trading)
    - Maximum open positions
    - Per-trade risk limits
    """

    def __init__(
        self,
        daily_loss_limit_pct: float = 0.03,
        weekly_loss_limit_pct: float = 0.06,
        monthly_loss_limit_pct: float = 0.10,
        max_drawdown_pct: float = 0.15,
        max_open_positions: int = 10,
        max_position_size_pct: float = 0.05,
    ) -> None:
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.weekly_loss_limit_pct = weekly_loss_limit_pct
        self.monthly_loss_limit_pct = monthly_loss_limit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_open_positions = max_open_positions
        self.max_position_size_pct = max_position_size_pct
        self._cache = RedisCache(prefix="trading", ttl=86400)

    async def check_trade_allowed(self, request: RiskCheckRequest, db: Any = None) -> RiskCheckResponse:
        """
        Comprehensive risk check before allowing a trade.
        Returns approval status with reasons.
        """
        reasons: list[str] = []
        warnings: list[str] = []

        # Check daily, weekly, and monthly loss limits
        if request.account_equity > 0:
            # Daily PNL Check
            daily_loss_pct = (
                -request.daily_pnl / request.account_equity if request.daily_pnl < 0 else 0.0
            )
            if daily_loss_pct >= self.daily_loss_limit_pct:
                reasons.append(
                    f"Daily loss limit reached: {daily_loss_pct:.1%} >= {self.daily_loss_limit_pct:.1%}"
                )
            elif daily_loss_pct >= self.daily_loss_limit_pct * 0.8:
                warnings.append(
                    f"Daily loss approaching limit: {daily_loss_pct:.1%} / {self.daily_loss_limit_pct:.1%}"
                )

            # Weekly PNL Check
            weekly_loss_pct = (
                -request.weekly_pnl / request.account_equity if request.weekly_pnl < 0 else 0.0
            )
            if weekly_loss_pct >= self.weekly_loss_limit_pct:
                reasons.append(
                    f"Weekly loss limit reached: {weekly_loss_pct:.1%} >= {self.weekly_loss_limit_pct:.1%}"
                )
            elif weekly_loss_pct >= self.weekly_loss_limit_pct * 0.8:
                warnings.append(
                    f"Weekly loss approaching limit: {weekly_loss_pct:.1%} / {self.weekly_loss_limit_pct:.1%}"
                )

            # Monthly PNL Check
            monthly_loss_pct = (
                -request.monthly_pnl / request.account_equity if request.monthly_pnl < 0 else 0.0
            )
            if monthly_loss_pct >= self.monthly_loss_limit_pct:
                reasons.append(
                    f"Monthly loss limit reached: {monthly_loss_pct:.1%} >= {self.monthly_loss_limit_pct:.1%}"
                )
            elif monthly_loss_pct >= self.monthly_loss_limit_pct * 0.8:
                warnings.append(
                    f"Monthly loss approaching limit: {monthly_loss_pct:.1%} / {self.monthly_loss_limit_pct:.1%}"
                )

        # Check max drawdown
        if request.current_drawdown_pct >= self.max_drawdown_pct:
            reasons.append(
                f"Max drawdown exceeded: {request.current_drawdown_pct:.1%} >= {self.max_drawdown_pct:.1%}"
            )
        elif request.current_drawdown_pct >= self.max_drawdown_pct * 0.8:
            warnings.append(
                f"Drawdown approaching max: {request.current_drawdown_pct:.1%} / {self.max_drawdown_pct:.1%}"
            )

        # Check open positions
        if request.open_positions >= self.max_open_positions:
            reasons.append(
                f"Max open positions reached: {request.open_positions} >= {self.max_open_positions}"
            )

        # Check position size
        if request.proposed_position_pct > self.max_position_size_pct:
            reasons.append(
                f"Position too large: {request.proposed_position_pct:.1%} > {self.max_position_size_pct:.1%}"
            )

        # Check circuit breaker flag in Redis
        circuit_breaker = await self._cache.get("circuit_breaker_active")
        if circuit_breaker:
            reasons.append("Circuit breaker is active - trading halted")

        approved = len(reasons) == 0
        if not approved:
            logger.warning("Trade rejected by risk check", reasons=reasons)
            if db is not None:
                from services.risk_management.domain.models import RiskEvent  # noqa: PLC0415
                import uuid  # noqa: PLC0415
                for reason in reasons:
                    severity = "warning"
                    if "circuit breaker" in reason.lower() or "drawdown" in reason.lower():
                        severity = "critical"
                    
                    event = RiskEvent(
                        id=uuid.uuid4(),
                        event_type="trade_check_failed",
                        severity=severity,
                        message=reason,
                        details={
                            "account_equity": request.account_equity,
                            "daily_pnl": request.daily_pnl,
                            "weekly_pnl": request.weekly_pnl,
                            "monthly_pnl": request.monthly_pnl,
                            "current_drawdown_pct": request.current_drawdown_pct,
                            "open_positions": request.open_positions,
                            "proposed_position_pct": request.proposed_position_pct
                        },
                        acknowledged=False,
                        created_at=datetime.now(UTC)
                    )
                    db.add(event)
                try:
                    await db.commit()
                except Exception as db_err:
                    logger.error("Failed to commit RiskEvents to database", error=str(db_err))
                    await db.rollback()
        elif warnings:
            logger.warning("Trade approved with warnings", warnings=warnings)

        return RiskCheckResponse(approved=approved, reasons=reasons, warnings=warnings)

    async def activate_circuit_breaker(self, reason: str) -> None:
        """Activate the circuit breaker to halt all trading."""
        await self._cache.set(
            "circuit_breaker_active",
            {
                "activated_at": datetime.now(UTC).isoformat(),
                "reason": reason,
            },
            ttl=86400,
        )
        logger.critical("CIRCUIT BREAKER ACTIVATED", reason=reason)

    async def deactivate_circuit_breaker(self) -> None:
        """Deactivate the circuit breaker."""
        await self._cache.delete("circuit_breaker_active")
        logger.info("Circuit breaker deactivated")

    async def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is currently active."""
        return await self._cache.exists("circuit_breaker_active")
