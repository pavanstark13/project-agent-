import datetime
from typing import Dict, Any

class DailyLossCap:
    """Simple risk manager that stops trading once a daily loss threshold is exceeded.

    Parameters
    ----------
    loss_cap : float
        Maximum cumulative loss (negative P&L) allowed per calendar day.
    """

    def __init__(self, loss_cap: float = 1000.0):
        self.loss_cap = loss_cap
        self.daily_losses: Dict[str, float] = {}

    def reset_day(self, date: str):
        self.daily_losses[date] = 0.0

    def update(self, timestamp: str, pnl: float) -> bool:
        """Update P&L for a given timestamp.

        Returns ``True`` if trading should continue, ``False`` if the loss cap has been hit.
        """
        # Extract date (YYYY-MM-DD) from ISO timestamp
        date = timestamp.split('T')[0]
        if date not in self.daily_losses:
            self.reset_day(date)
        self.daily_losses[date] += pnl
        return self.daily_losses[date] >= -self.loss_cap

    def is_allowed(self, timestamp: str) -> bool:
        """Check whether trading is still allowed for the given timestamp.
        """
        date = timestamp.split('T')[0]
        return self.daily_losses.get(date, 0.0) >= -self.loss_cap

    def __repr__(self) -> str:
        return f"DailyLossCap(loss_cap={self.loss_cap})"
