"""Backtesting service for strategy performance evaluation."""

from datetime import datetime

import numpy as np
import structlog

from services.strategy_engine.services.signal_generator import STRATEGY_REGISTRY
from services.strategy_engine.strategies.base import Candle, StrategySignal

logger = structlog.get_logger(__name__)


class BacktestEngine:
    """
    Event-driven backtesting engine.

    Simulates strategy execution on historical data bar-by-bar.
    """

    def __init__(self, initial_capital: float = 100_000.0, commission: float = 0.001) -> None:
        self.initial_capital = initial_capital
        self.commission = commission  # 0.1% per trade

    def run(
        self,
        ohlcv_data: list[dict],
        strategy_names: list[str] | None = None,
        strategy_params: dict | None = None,
    ) -> dict:
        """
        Run backtest on historical data.

        Returns performance metrics dict.
        """
        if len(ohlcv_data) < 60:
            raise ValueError("Need at least 60 bars for backtesting")

        candles = [
            Candle(
                timestamp=bar.get("timestamp", datetime.utcnow()),
                open=float(bar["open"]),
                high=float(bar["high"]),
                low=float(bar["low"]),
                close=float(bar["close"]),
                volume=float(bar["volume"]),
            )
            for bar in ohlcv_data
        ]

        to_run = strategy_names or ["order_block", "ma_crossover"]
        params = strategy_params or {}
        strategies = []
        for name in to_run:
            cls = STRATEGY_REGISTRY.get(name)
            if cls:
                strategies.append(cls(parameters=params.get(name)))

        capital = self.initial_capital
        equity_curve = [capital]
        trades: list[dict] = []
        position: dict | None = None
        peak_equity = capital

        # Walk-forward simulation
        for i in range(50, len(candles)):
            window = candles[:i]
            current_candle = candles[i]

            # Close position if stop/TP hit
            if position is not None:
                if position["direction"] == "long":
                    if current_candle.low <= position["stop_loss"]:
                        pnl = (position["stop_loss"] - position["entry_price"]) * position["qty"]
                        capital += pnl - abs(pnl * self.commission)
                        trades.append(
                            {
                                **position,
                                "exit_price": position["stop_loss"],
                                "pnl": pnl,
                                "exit_reason": "stop_loss",
                            }
                        )
                        position = None
                    elif current_candle.high >= position["take_profit"]:
                        pnl = (position["take_profit"] - position["entry_price"]) * position["qty"]
                        capital += pnl - abs(pnl * self.commission)
                        trades.append(
                            {
                                **position,
                                "exit_price": position["take_profit"],
                                "pnl": pnl,
                                "exit_reason": "take_profit",
                            }
                        )
                        position = None
                elif position["direction"] == "short":
                    if current_candle.high >= position["stop_loss"]:
                        pnl = (position["entry_price"] - position["stop_loss"]) * position["qty"]
                        capital += pnl - abs(pnl * self.commission)
                        trades.append(
                            {
                                **position,
                                "exit_price": position["stop_loss"],
                                "pnl": pnl,
                                "exit_reason": "stop_loss",
                            }
                        )
                        position = None
                    elif current_candle.low <= position["take_profit"]:
                        pnl = (position["entry_price"] - position["take_profit"]) * position["qty"]
                        capital += pnl - abs(pnl * self.commission)
                        trades.append(
                            {
                                **position,
                                "exit_price": position["take_profit"],
                                "pnl": pnl,
                                "exit_reason": "take_profit",
                            }
                        )
                        position = None

            # Generate signals from strategies
            if position is None:
                all_signals: list[StrategySignal] = []
                for strategy in strategies:
                    try:
                        signals = strategy.generate_signals(window)
                        all_signals.extend(signals)
                    except Exception:
                        pass

                if all_signals:
                    best_signal = max(all_signals, key=lambda s: s.strength)
                    if (
                        best_signal.strength >= 0.6
                        and best_signal.stop_loss
                        and best_signal.take_profit
                    ):
                        entry_price = current_candle.open
                        risk_pct = 0.01  # 1% risk per trade
                        risk_amount = capital * risk_pct
                        risk_per_unit = abs(entry_price - best_signal.stop_loss)
                        qty = risk_amount / risk_per_unit if risk_per_unit > 0 else 0

                        if qty > 0:
                            position = {
                                "direction": best_signal.direction,
                                "entry_price": entry_price,
                                "stop_loss": best_signal.stop_loss,
                                "take_profit": best_signal.take_profit,
                                "qty": qty,
                                "entry_idx": i,
                                "strategy": best_signal.metadata.get("strategy", "unknown"),
                            }
                            capital -= entry_price * qty * self.commission

            equity_curve.append(capital)
            peak_equity = max(peak_equity, capital)

        # Calculate metrics
        winning = [t for t in trades if t["pnl"] > 0]
        losing = [t for t in trades if t["pnl"] <= 0]
        total_trades = len(trades)
        win_rate = len(winning) / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in winning)
        gross_loss = abs(sum(t["pnl"] for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        total_return_pct = (capital - self.initial_capital) / self.initial_capital
        max_drawdown_pct = self._compute_max_drawdown(equity_curve)
        sharpe = self._compute_sharpe(equity_curve)
        sortino = self._compute_sortino(equity_curve)

        # CAGR calculation (assuming daily candles)
        total_days = len(candles) / 252.0 if len(candles) > 0 else 1.0
        cagr = (capital / self.initial_capital) ** (1.0 / total_days) - 1.0 if capital > 0 else -1.0

        # Expectancy calculation
        avg_win = np.mean([t["pnl"] for t in winning]) if winning else 0.0
        avg_loss = abs(np.mean([t["pnl"] for t in losing])) if losing else 0.0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        # Strategy rejection check (Minimum Sharpe of 1.5, positive expectancy, and at least 5 trades)
        strategy_approved = True
        rejection_reasons = []
        if sharpe < 1.5:
            strategy_approved = False
            rejection_reasons.append(f"Sharpe Ratio {sharpe:.2f} is below minimum requirement of 1.5")
        if expectancy <= 0:
            strategy_approved = False
            rejection_reasons.append("Strategy expectancy is negative or zero")
        if total_trades < 5:
            strategy_approved = False
            rejection_reasons.append(f"Total trades count ({total_trades}) is too low for statistical validity")

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(win_rate, 4),
            "total_return_pct": round(total_return_pct, 4),
            "max_drawdown_pct": round(max_drawdown_pct, 4),
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "cagr": round(cagr, 4),
            "expectancy": round(expectancy, 2),
            "profit_factor": round(profit_factor, 4),
            "initial_capital": self.initial_capital,
            "final_capital": round(capital, 2),
            "strategy_approved": strategy_approved,
            "rejection_reasons": rejection_reasons,
        }

    def _compute_max_drawdown(self, equity_curve: list[float]) -> float:
        eq = np.array(equity_curve)
        peak = np.maximum.accumulate(eq)
        drawdown = (peak - eq) / peak
        return float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

    def _compute_sharpe(self, equity_curve: list[float], risk_free: float = 0.02) -> float:
        eq = np.array(equity_curve)
        if len(eq) < 2:
            return 0.0
        returns = np.diff(eq) / eq[:-1]
        if returns.std() == 0:
            return 0.0
        # Annualize (assuming daily bars)
        sharpe = (returns.mean() * 252 - risk_free) / (returns.std() * np.sqrt(252))
        return float(sharpe)

    def _compute_sortino(self, equity_curve: list[float], risk_free: float = 0.02) -> float:
        eq = np.array(equity_curve)
        if len(eq) < 2:
            return 0.0
        returns = np.diff(eq) / eq[:-1]
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return 0.0
        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0.0
        sortino = (returns.mean() * 252 - risk_free) / (downside_std * np.sqrt(252))
        return float(sortino)
