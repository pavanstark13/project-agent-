"""Unit tests for YahooFinanceAdapter."""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from services.market_data.adapters.yfinance_adapter import YahooFinanceAdapter
from services.market_data.domain.schemas import Timeframe


class TestYahooFinanceAdapter:
    """Tests for YahooFinanceAdapter using mocked yfinance client."""

    def setup_method(self):
        self.adapter = YahooFinanceAdapter()

    @pytest.mark.asyncio
    async def test_get_quote(self):
        with patch("services.market_data.adapters.yfinance_adapter.yf.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_ticker.fast_info = {"lastPrice": 150.0, "lastVolume": 1000, "open": 148.0}
            mock_ticker_class.return_value = mock_ticker

            res = await self.adapter.get_quote("AAPL")
            assert res.ticker == "AAPL"
            assert res.last == 150.0
            assert res.change == 2.0
            assert res.change_pct == pytest.approx(2.0 / 148.0)
            assert res.volume == 1000.0

    @pytest.mark.asyncio
    async def test_get_historical_bars(self):
        with patch("services.market_data.adapters.yfinance_adapter.yf.Ticker") as mock_ticker_class:
            mock_ticker = MagicMock()
            mock_df = pd.DataFrame(
                {
                    "Open": [100.0, 101.0],
                    "High": [105.0, 106.0],
                    "Low": [99.0, 100.0],
                    "Close": [102.0, 103.0],
                    "Volume": [1000, 1100],
                },
                index=pd.DatetimeIndex([datetime(2026, 6, 1, 10), datetime(2026, 6, 1, 11)]),
            )
            mock_ticker.history.return_value = mock_df
            mock_ticker_class.return_value = mock_ticker

            bars = await self.adapter.get_historical_bars(
                "AAPL", Timeframe.H1, datetime(2026, 6, 1)
            )
            assert len(bars) == 2
            assert bars[0].open == 100.0
            assert bars[0].close == 102.0
            assert bars[1].open == 101.0
            assert bars[1].close == 103.0
