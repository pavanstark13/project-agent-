"""Unit tests for LossLimiter risk engine."""

from unittest.mock import AsyncMock, patch
import pytest

from services.risk_management.domain.schemas import RiskCheckRequest
from services.risk_management.services.loss_limiter import LossLimiter


class TestLossLimiter:
    """Tests for LossLimiter risk checks."""

    @pytest.mark.asyncio
    async def test_loss_limiter_limits(self):
        # Mock RedisCache
        with patch("services.risk_management.services.loss_limiter.RedisCache") as mock_cache_class:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_cache.exists.return_value = False
            mock_cache_class.return_value = mock_cache

            limiter = LossLimiter(
                daily_loss_limit_pct=0.03,
                weekly_loss_limit_pct=0.06,
                monthly_loss_limit_pct=0.10,
                max_drawdown_pct=0.15,
                max_open_positions=5,
                max_position_size_pct=0.05,
            )

            # 1. Normal Trade (all clear)
            req = RiskCheckRequest(
                account_equity=100000.0,
                daily_pnl=0.0,
                weekly_pnl=0.0,
                monthly_pnl=0.0,
                current_drawdown_pct=0.01,
                open_positions=2,
                proposed_position_pct=0.02,
            )
            res = await limiter.check_trade_allowed(req)
            assert res.approved is True
            assert len(res.reasons) == 0

            # 2. Daily Loss Limit breached
            req_daily = RiskCheckRequest(
                account_equity=100000.0,
                daily_pnl=-3100.0,  # -3.1% daily PnL
                weekly_pnl=-3100.0,
                monthly_pnl=-3100.0,
                current_drawdown_pct=0.01,
                open_positions=2,
                proposed_position_pct=0.02,
            )
            res_daily = await limiter.check_trade_allowed(req_daily)
            assert res_daily.approved is False
            assert any("Daily loss limit reached" in r for r in res_daily.reasons)

            # 3. Weekly Loss Limit breached
            req_weekly = RiskCheckRequest(
                account_equity=100000.0,
                daily_pnl=0.0,
                weekly_pnl=-6500.0,  # -6.5% weekly PnL
                monthly_pnl=-6500.0,
                current_drawdown_pct=0.01,
                open_positions=2,
                proposed_position_pct=0.02,
            )
            res_weekly = await limiter.check_trade_allowed(req_weekly)
            assert res_weekly.approved is False
            assert any("Weekly loss limit reached" in r for r in res_weekly.reasons)

            # 4. Monthly Loss Limit breached
            req_monthly = RiskCheckRequest(
                account_equity=100000.0,
                daily_pnl=0.0,
                weekly_pnl=0.0,
                monthly_pnl=-11000.0,  # -11.0% monthly PnL
                current_drawdown_pct=0.01,
                open_positions=2,
                proposed_position_pct=0.02,
            )
            res_monthly = await limiter.check_trade_allowed(req_monthly)
            assert res_monthly.approved is False
            assert any("Monthly loss limit reached" in r for r in res_monthly.reasons)

            # 5. Circuit Breaker active
            mock_cache.get.return_value = {"reason": "Manual Halt"}
            mock_cache.exists.return_value = True
            res_cb = await limiter.check_trade_allowed(req)
            assert res_cb.approved is False
            assert any("Circuit breaker is active" in r for r in res_cb.reasons)
