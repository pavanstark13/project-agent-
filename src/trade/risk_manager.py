from datetime import datetime
from src.trade.config import Settings

class TrailingStopLoss:
    def __init__(self, trailing_pct: float):
        """
        trailing_pct: decimal representation of percentage (e.g. 0.025 for 2.5%)
        """
        self.trailing_pct = trailing_pct
        self.highest_price = 0.0
        self.stop_price = 0.0
        self.is_active = False

    def update_price(self, current_price: float) -> bool:
        """
        Updates highest price and checks if current price triggers stop loss.
        Returns True if stop loss triggered, False otherwise.
        """
        if not self.is_active:
            self.highest_price = current_price
            self.stop_price = current_price * (1 - self.trailing_pct)
            self.is_active = True
            return False
            
        if current_price > self.highest_price:
            self.highest_price = current_price
            self.stop_price = current_price * (1 - self.trailing_pct)
            
        if current_price <= self.stop_price:
            self.is_active = False # Reset upon triggering
            return True
            
        return False

class DailyLossCap:
    def __init__(self, daily_loss_cap_pct: float, initial_equity: float):
        """
        daily_loss_cap_pct: e.g. 0.05 for 5% max loss per day
        """
        self.daily_loss_cap_pct = daily_loss_cap_pct
        self.start_equity = initial_equity
        self.current_equity = initial_equity
        self.trading_date = datetime.utcnow().date()
        self.halt_trading = False

    def update_equity(self, current_equity: float):
        """
        Updates daily equity and checks against the cap. 
        Automatically resets at the start of a new day.
        """
        today = datetime.utcnow().date()
        if today != self.trading_date:
            # New day, reset starting equity and allow trading again
            self.trading_date = today
            self.start_equity = current_equity
            self.halt_trading = False
            
        self.current_equity = current_equity
        loss_pct = (self.start_equity - current_equity) / self.start_equity
        
        if loss_pct >= self.daily_loss_cap_pct:
            self.halt_trading = True
            
        return self.halt_trading

    def can_trade(self) -> bool:
        return not self.halt_trading
