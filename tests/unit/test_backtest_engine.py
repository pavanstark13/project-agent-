"""Unit tests for BacktestEngine."""

from datetime import datetime, timedelta
import pytest

from services.strategy_engine.services.backtest import BacktestEngine


class TestBacktestEngine:
    """Tests for BacktestEngine metrics and validation filters."""

    def setup_method(self):
        self.engine = BacktestEngine(initial_capital=10000.0, commission=0.0)

    def test_backtest_calc_metrics_approved(self):
        # Generate 100 dummy daily bars
        bars = []
        base_time = datetime(2026, 6, 1)
        for i in range(100):
            # Create a simple trend that the MA crossover strategy can pick up
            price = 100.0 + i * 0.8
            if i % 15 == 0:
                price -= 5.0  # dip to trigger signals
            bars.append(
                {
                    "timestamp": base_time + timedelta(days=i),
                    "open": price,
                    "high": price + 2.0,
                    "low": price - 2.0,
                    "close": price + 0.5,
                    "volume": 1000.0,
                }
            )

        res = self.engine.run(bars, strategy_names=["ma_crossover"])

        assert "cagr" in res
        assert "sortino_ratio" in res
        assert "expectancy" in res
        assert "strategy_approved" in res
        assert "rejection_reasons" in res
        assert isinstance(res["strategy_approved"], bool)
        assert isinstance(res["rejection_reasons"], list)
