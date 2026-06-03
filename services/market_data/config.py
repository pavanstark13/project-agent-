"""Market Data Service configuration."""

from functools import lru_cache

from shared.config import Settings


class MarketDataSettings(Settings):
    """Market Data service-specific settings."""

    service_name: str = "market-data"
    service_port: int = 8001
    primary_data_provider: str = "yfinance"

    # WebSocket settings
    ws_ping_interval: int = 30
    ws_ping_timeout: int = 10

    # Data refresh intervals (seconds)
    snapshot_refresh_interval: int = 5
    historical_cache_ttl: int = 3600  # 1 hour


@lru_cache
def get_settings() -> MarketDataSettings:
    return MarketDataSettings()
