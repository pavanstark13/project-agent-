import vectorbt as vbt
import pandas as pd
from typing import List, Dict

def run_backtest(signal: List[float]) -> Dict:
    """Simple backtest using vectorbt.
    * `signal` is a list of numeric values representing a trading signal (e.g., forecasted returns).
    * For demonstration we generate a synthetic price series and feed the signal as entry/exit.
    Returns a dictionary with key performance metrics.
    """
    # Create a synthetic price series (100 days) – start at 100, random walk
    price = pd.Series(100 + pd.Series(signal).cumsum()).ffill()
    # Convert signal to entry/exit boolean series (positive => long, negative => short)
    entries = pd.Series([s > 0 for s in signal])
    exits = pd.Series([s <= 0 for s in signal])
    # Use vectorbt to compute portfolio
    portfolio = vbt.Portfolio.from_signals(price, entries, exits, freq='1D')
    stats = portfolio.stats()
    # vectorbt stats() returns a Series with human-readable keys
    def _get(key, fallback=0.0):
        val = stats.get(key, fallback)
        return float(val) if hasattr(val, '__float__') else fallback
    return {
        "total_return": _get('Total Return [%]') / 100,
        "sharpe": _get('Sharpe Ratio'),
        "max_dd": _get('Max Drawdown [%]') / 100,
        "win_rate": _get('Win Rate [%]') / 100,
        "trades": int(_get('Total Trades', 0)),
    }
