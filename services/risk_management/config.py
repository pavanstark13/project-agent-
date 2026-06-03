"""Risk Management Service configuration."""

from functools import lru_cache

from shared.config import Settings


class RiskManagementSettings(Settings):
    service_name: str = "risk-management"
    service_port: int = 8003
    default_risk_per_trade: float = 0.01
    default_max_position_pct: float = 0.05
    default_daily_loss_limit: float = 0.03
    default_weekly_loss_limit: float = 0.06
    default_monthly_loss_limit: float = 0.10
    default_max_drawdown: float = 0.15
    default_max_open_positions: int = 10


@lru_cache
def get_settings() -> RiskManagementSettings:
    return RiskManagementSettings()
