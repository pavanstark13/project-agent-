import io
import ccxt
import boto3
import pandas as pd
from typing import Optional, List
from src.trade.config import Settings

class CloudDataFetcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.bucket = settings.s3_bucket_name
        self.exchange = getattr(ccxt, settings.exchange_name)({
            'apiKey': settings.api_key,
            'secret': settings.api_secret,
            'enableRateLimit': True,
        })
        if settings.deployment_mode == "paper":
            try:
                self.exchange.set_sandbox_mode(True)
            except Exception:
                pass  # not all exchanges support sandbox mode

    def fetch_and_upload(self, symbol: str, timeframe: str = '1h', limit: int = 1000) -> str:
        """Fetch OHLCV data from exchange and upload directly to S3 as parquet."""
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Write to in-memory parquet buffer
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        
        # Upload to S3
        file_key = f"market_data/{symbol.replace('/', '_')}_{timeframe}.parquet"
        self.s3_client.upload_fileobj(buffer, self.bucket, file_key)
        return file_key

    def download_data(self, symbol: str, timeframe: str = '1h') -> pd.DataFrame:
        """Download historical parquet data from S3 to a pandas DataFrame."""
        file_key = f"market_data/{symbol.replace('/', '_')}_{timeframe}.parquet"
        buffer = io.BytesIO()
        self.s3_client.download_fileobj(self.bucket, file_key, buffer)
        buffer.seek(0)
        df = pd.read_parquet(buffer)
        return df
