import os
from typing import Dict, Any

from src.trade.config import Settings

class StrategyEngine:
    """Simple rule‑based strategy engine with validation and order spec generation.

    The engine reads configuration thresholds from ``Settings`` and provides:
    * ``validate(backtest_res)`` – checks win‑rate and Sharpe ratio against the
      configured minima.
    * ``decide(backtest_res, multimodal_data)`` – returns an order dictionary
      compatible with ``OrderManager.execute``. It includes a trailing stop‑loss
      based on ``Settings.trailing_stop_pct``.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.settings = Settings()

    # ---------------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------------
    def validate(self, backtest_res: Dict[str, Any]) -> bool:
        """Validate a back‑test result.

        Expected ``backtest_res`` keys:
        * ``win_rate`` – float (0‑1)
        * ``sharpe`` – float
        * ``total_return`` – float (decimal, e.g., 0.12 for 12 %)
        Returns ``True`` if both win‑rate and Sharpe meet the configured
        thresholds, otherwise ``False``.
        """
        win_rate = backtest_res.get("win_rate")
        sharpe = backtest_res.get("sharpe")
        # Default to 0 if missing
        win_rate = win_rate if win_rate is not None else 0.0
        sharpe = sharpe if sharpe is not None else 0.0
        return (
            win_rate >= self.settings.win_rate_min
            and sharpe >= self.settings.validation_sharpe_min
        )

    # ---------------------------------------------------------------------
    # Decision making
    # ---------------------------------------------------------------------
    def decide(self, backtest_res: Dict[str, Any], multimodal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an order specification.

        The simplistic implementation uses the sign of ``total_return`` to decide
        long (positive) or short (negative). It respects ``default_size`` and adds
        a trailing stop‑loss based on the entry price.
        """
        total_ret = backtest_res.get("total_return", 0)
        if total_ret > 0:
            side = "buy"
        elif total_ret < 0:
            side = "sell"
        else:
            return {"side": None, "reason": "no_signal"}

        size = self.settings.default_size
        # Determine entry price from latest OHLCV if available
        entry_price = 0.0
        if "ohlcv" in multimodal_data:
            df = multimodal_data["ohlcv"]
            if not df.empty:
                entry_price = float(df["close"].iloc[-1])

        trailing_pct = self.settings.trailing_stop_pct
        if side == "buy":
            stop_price = entry_price * (1 - trailing_pct)
            take_profit = entry_price * (1 + 2 * trailing_pct)
        else:
            stop_price = entry_price * (1 + trailing_pct)
            take_profit = entry_price * (1 - 2 * trailing_pct)

        return {
            "symbol": self.symbol,
            "side": side,
            "size": size,
            "price": entry_price,
            "stop_loss": stop_price,
            "take_profit": take_profit,
        }
