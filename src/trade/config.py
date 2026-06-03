import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuration for trade execution.
    Values are read from environment variables or a .env file.
    """

    # Core exchange settings
    exchange_name: str = os.getenv("EXCHANGE_NAME", "binance")
    api_key: str = os.getenv("EXCHANGE_API_KEY", "YOUR_API_KEY")
    api_secret: str = os.getenv("EXCHANGE_API_SECRET", "YOUR_SECRET")
    default_symbol: str = os.getenv("DEFAULT_SYMBOL", "BTC/USDT")
    default_size: float = float(os.getenv("DEFAULT_SIZE", "0.001"))

    # Risk management
    stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "0.02"))  # 2%
    take_profit_pct: float = float(os.getenv("TAKE_PROFIT_PCT", "0.05"))  # 5%
    trailing_stop_pct: float = float(os.getenv("TRAILING_STOP_PCT", "0.025"))  # 2.5%
    daily_loss_cap_pct: float = float(os.getenv("DAILY_LOSS_CAP_PCT", "0.05"))  # 5% of equity per day
    win_rate_min: float = float(os.getenv("WIN_RATE_MIN", "0.55"))  # 55% win rate threshold

    # Validation thresholds
    validation_sharpe_min: float = float(os.getenv("VALIDATION_SHARPE_MIN", "0.5"))
    validation_return_min: float = float(os.getenv("VALIDATION_RETURN_MIN", "0.0"))

    # Scheduler settings
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))  # default 5 minutes
    deployment_mode: str = os.getenv("DEPLOYMENT_MODE", "paper")  # paper or live
    data_source: str = os.getenv("DATA_SOURCE", "ccxt")  # ccxt or yfinance

    # Cloud Storage settings
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "my-trading-agent-bucket")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
