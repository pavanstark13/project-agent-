"""Yahoo Finance market data adapter."""

import asyncio
from datetime import datetime
import yfinance as yf
import pandas as pd
from typing import Any
import structlog

from services.market_data.adapters.base import BaseBrokerAdapter
from services.market_data.domain.schemas import MarketQuote, OHLCVBase, Timeframe

logger = structlog.get_logger(__name__)


class YahooFinanceAdapter(BaseBrokerAdapter):
    """Yahoo Finance market data adapter."""

    @property
    def name(self) -> str:
        return "yfinance"

    async def connect(self) -> None:
        logger.info("Yahoo Finance adapter connected")

    async def disconnect(self) -> None:
        logger.info("Yahoo Finance adapter disconnected")

    def _fetch_quote_sync(self, ticker: str) -> MarketQuote:
        t = yf.Ticker(ticker)
        # fast_info is fast and parses minimum overhead
        info = t.fast_info
        
        last_price = info.get("lastPrice")
        if last_price is None or pd.isna(last_price):
            # Fallback to daily history
            hist = t.history(period="1d")
            if not hist.empty:
                last_price = hist["Close"].iloc[-1]
                volume = hist["Volume"].iloc[-1]
            else:
                raise ValueError(f"No price data found for {ticker}")
        else:
            volume = info.get("lastVolume", 0)

        open_price = info.get("open")
        change = None
        change_pct = None
        if open_price and last_price:
            change = last_price - open_price
            change_pct = change / open_price if open_price > 0 else 0.0

        return MarketQuote(
            ticker=ticker,
            bid=last_price,  # default to last price
            ask=last_price,
            last=last_price,
            change=change,
            change_pct=change_pct,
            volume=float(volume) if volume else None,
            timestamp=datetime.now(),
        )

    async def get_quote(self, ticker: str) -> MarketQuote:
        """Get latest quote for a symbol."""
        try:
            return await asyncio.to_thread(self._fetch_quote_sync, ticker)
        except Exception as e:
            logger.error("Failed to fetch quote from yfinance", ticker=ticker, error=str(e))
            raise

    async def get_quotes(self, tickers: list[str]) -> list[MarketQuote]:
        """Get latest quotes for multiple symbols."""
        tasks = [self.get_quote(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        quotes = []
        for ticker, res in zip(tickers, results):
            if isinstance(res, Exception):
                logger.error("Failed to fetch quote in batch", ticker=ticker, error=str(res))
            else:
                quotes.append(res)
        return quotes

    def _fetch_historical_bars_sync(
        self,
        ticker: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime | None,
        limit: int,
    ) -> list[OHLCVBase]:
        t = yf.Ticker(ticker)
        tf_map = {
            Timeframe.M1: "1m",
            Timeframe.M5: "5m",
            Timeframe.M15: "15m",
            Timeframe.M30: "30m",
            Timeframe.H1: "1h",
            Timeframe.H4: "1h",  # Fallback to hourly
            Timeframe.D1: "1d",
            Timeframe.W1: "1wk",
        }
        interval = tf_map.get(timeframe, "1d")
        
        hist = t.history(
            start=start,
            end=end,
            interval=interval,
            keepna=False,
        )
        
        if hist.empty:
            return []
            
        if len(hist) > limit:
            hist = hist.tail(limit)

        bars = []
        for index, row in hist.iterrows():
            ts = index.to_pydatetime()
            bars.append(
                OHLCVBase(
                    timeframe=timeframe,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                    timestamp=ts,
                )
            )
        return bars

    async def get_historical_bars(
        self,
        ticker: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime | None = None,
        limit: int = 500,
    ) -> list[OHLCVBase]:
        """Get historical OHLCV bars."""
        try:
            return await asyncio.to_thread(
                self._fetch_historical_bars_sync,
                ticker,
                timeframe,
                start,
                end,
                limit,
            )
        except Exception as e:
            logger.error("Failed to fetch historical bars from yfinance", ticker=ticker, error=str(e))
            return []
