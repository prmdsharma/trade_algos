"""
Exit engine: decides when to close an open option position.

Implements:
- Target and stop-loss based on option premium percentage move
- Opposite-signal exit using EMA9/EMA21
- Time-based forced exit at end-of-day
"""

import datetime


class ExitEngine:
    def __init__(self, config):
        # +12% target, -8% stop loss (from spec)
        self.target_pct = config["trade_params"]["target_pct"]
        self.sl_pct = config["trade_params"]["stop_loss_pct"]
        # Afternoon end time for forced EOD exit
        self._afternoon_end = datetime.datetime.strptime(
            config["windows"]["afternoon_end"], "%H:%M"
        ).time()

    def check_exit(self, position, current_candle):
        """
        Checks Target, SL, Opposite Signal, and End-of-Day.

        Assumes `current_candle['close']` is the option premium.
        In live trading you should replace this with actual option LTP.
        """
        entry_price = position["entry_price"]
        current_premium = current_candle["close"]

        if entry_price <= 0:
            return False, None

        pct_change = (current_premium - entry_price) / entry_price

        # 1) Target hit
        if pct_change >= self.target_pct:
            return True, "Target Hit"

        # 2) Stop-loss hit
        if pct_change <= -self.sl_pct:
            return True, "Stop Loss Hit"

        # 3) Opposite signal (EMA cross) – exit regardless of P&L
        ema9 = current_candle.get("EMA9")
        ema21 = current_candle.get("EMA21")

        if ema9 is not None and ema21 is not None:
            if position["type"] == "CE" and ema9 < ema21:
                return True, "Opposite Signal"

            if position["type"] == "PE" and ema9 > ema21:
                return True, "Opposite Signal"

        # 4) End-of-day forced exit – spec requires no overnight positions
        candle_time = current_candle.get("time")
        if candle_time is not None:
            # Backtest: use the candle's own timestamp
            if hasattr(candle_time, "time"):
                now = candle_time.time()   # datetime → time
            else:
                now = candle_time          # already a time object
        else:
            now = datetime.datetime.now().time()

        if now >= self._afternoon_end:
            return True, "End of Day"

        return False, None

