import datetime
from typing import Optional

from core.utils import get_today_date


class RiskEngine:
    """
    Handles intraday risk controls and daily lifecycle.
    """

    def __init__(self, config):
        self.cfg = config
        self.trades_today = 0
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.current_date = get_today_date()

    def ensure_current_day(self, date_override: Optional[datetime.date] = None):
        """
        If the calendar day has changed, reset daily metrics.
        Call this from the main loop/on_candle before checks.
        """
        today = date_override or get_today_date()
        if today != self.current_date:
            self.logger_reset(today)
            self.reset_for_new_day(today)

    def logger_reset(self, new_date):
        # We don't have a logger in RiskEngine yet, but we should probably log the day change
        print(f"--- Day Change detected. Resetting RiskEngine for {new_date} ---")

    def reset_for_new_day(self, new_date: Optional[datetime.date] = None):
        """
        Reset counters at the start of a new trading day.
        """
        self.trades_today = 0
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.current_date = new_date or get_today_date()

    def is_trading_window_open(self, candle_time: Optional[datetime.time] = None):
        """
        Checks whether the given time falls within a trading window.

        In live mode, uses datetime.now().  In backtest mode, pass the
        candle's timestamp so the check is deterministic.
        """
        now = candle_time or datetime.datetime.now().time()
        m_start = datetime.datetime.strptime(
            self.cfg["windows"]["morning_start"], "%H:%M"
        ).time()
        m_end = datetime.datetime.strptime(
            self.cfg["windows"]["morning_end"], "%H:%M"
        ).time()
        a_start = datetime.datetime.strptime(
            self.cfg["windows"]["afternoon_start"], "%H:%M"
        ).time()
        a_end = datetime.datetime.strptime(
            self.cfg["windows"]["afternoon_end"], "%H:%M"
        ).time()

        return (m_start <= now <= m_end) or (a_start <= now <= a_end)

    def is_end_of_day(self, candle_time: Optional[datetime.time] = None) -> bool:
        """
        True once we are past the configured afternoon_end time.

        Pass candle_time for backtest determinism.
        """
        now = candle_time or datetime.datetime.now().time()
        a_end = datetime.datetime.strptime(
            self.cfg["windows"]["afternoon_end"], "%H:%M"
        ).time()
        return now > a_end

    def can_trade(self):
        """Validates against daily limits."""
        # if self.trades_today >= self.cfg["risk"]["max_trades_per_day"]:
        #     return False
        if self.consecutive_losses >= self.cfg["risk"]["max_consecutive_losses"]:
            return False

        loss_limit = (
            self.cfg["account"]["initial_capital"]
            * self.cfg["risk"]["daily_loss_limit_pct"]
        )
        if self.daily_pnl <= -loss_limit:
            return False

        return True

    def update_metrics(self, pnl):
        self.daily_pnl += pnl
        self.trades_today += 1
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    # ---- Convenience accessors ----

    def is_loss_limit_breached(self) -> bool:
        """True when the daily PnL exceeds the configured loss ceiling."""
        loss_limit = (
            self.cfg["account"]["initial_capital"]
            * self.cfg["risk"]["daily_loss_limit_pct"]
        )
        return self.daily_pnl <= -loss_limit

    def get_daily_pnl(self) -> float:
        return self.daily_pnl

