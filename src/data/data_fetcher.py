import os
import pandas as pd
from datetime import datetime, timedelta

# Optional imports guarded to avoid errors if packages missing
try:
    import ccxt
except ImportError:
    ccxt = None
try:
    import yfinance as yf
except ImportError:
    yf = None

class DataFetcher:
    """Fetch OHLCV data for a given symbol using the configured data source.

    The data source is read from the Settings configuration ("ccxt" or "yfinance").
    For crypto symbols (e.g., "BTC/USDT") it uses ccxt and Binance futures testnet.
    For equity symbols (e.g., "AAPL") it uses yfinance.
    """

    def __init__(self, settings):
        self.settings = settings
        self.source = settings.data_source.lower()
        if self.source == "ccxt" and ccxt is None:
            raise RuntimeError("ccxt package is required for ccxt data source.")
        if self.source == "yfinance" and yf is None:
            raise RuntimeError("yfinance package is required for yfinance data source.")
        if self.source == "ccxt":
            # Initialise Binance (testnet) exchange via ccxt
            self.exchange = getattr(ccxt, settings.exchange_name)({
                "apiKey": settings.api_key,
                "secret": settings.api_secret,
                "enableRateLimit": True,
            })
            # Ensure we are on testnet if the user wants it
            if getattr(self.exchange, "has", {}).get("test"):
                self.exchange.set_sandbox_mode(True)
        else:
            self.exchange = None

    def fetch(self, symbol: str, timeframe: str = "1h", lookback_hours: int = 24):
        """Return a pandas DataFrame with OHLCV data.

        Parameters
        ----------
        symbol: str
            Trading pair or ticker.
        timeframe: str, default "1h"
            CCXT timeframe string (e.g., "1h", "5m"). For yfinance we use the same string when possible.
        lookback_hours: int, default 24
            How many hours of data to retrieve.
        """
        end_ts = int(datetime.utcnow().timestamp() * 1000)
        start_ts = end_ts - lookback_hours * 60 * 60 * 1000
        if self.source == "ccxt":
            # ccxt fetch_ohlcv expects milliseconds timestamps
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=start_ts, limit=None)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        else:
            # yfinance works with period strings; we convert lookback_hours
            period = f"{lookback_hours}h"
            ticker = yf.Ticker(symbol)
            hist = ticker.history(interval=timeframe, period=period)
            hist = hist.reset_index().rename(columns={"Datetime": "timestamp"})
            return hist
