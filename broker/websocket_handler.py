"""
WebSocket / streaming handler for live market data.

This is a skeleton: wire it to KiteTicker (or any other feed) to
emit 1-min candles that the rest of the system can consume.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


class CandleBuilder:
    """
    Utility to aggregate ticks into 1-min OHLCV candles.
    """

    def __init__(self):
        self._ticks: List[Dict[str, Any]] = []

    def add_tick(self, tick: Dict[str, Any]) -> None:
        """
        tick must contain: time (datetime), last_price, volume.
        """
        self._ticks.append(tick)

    def build_candle(self) -> Dict[str, Any]:
        if not self._ticks:
            raise ValueError("No ticks to build candle from.")

        df = pd.DataFrame(self._ticks)
        df = df.sort_values("time")

        o = df["last_price"].iloc[0]
        h = df["last_price"].max()
        l = df["last_price"].min()
        c = df["last_price"].iloc[-1]
        v = df["volume"].sum()

        candle_time = df["time"].iloc[-1].replace(second=0, microsecond=0)

        # Clear consumed ticks
        self._ticks.clear()

        return {
            "time": candle_time,
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": int(v),
        }


class WebSocketHandlerSkeleton:
    """
    Skeleton interface for a live WebSocket handler.

    You should:
    - Plug this into `KiteTicker` (kiteconnect) or your feed of choice.
    - On each completed 1-min interval, call `on_candle(candle_dict)`.
    """

    def __init__(self, on_candle: Callable[[Dict[str, Any]], None]):
        self.on_candle = on_candle
        self.candle_builder = CandleBuilder()
        self._current_minute: Optional[int] = None

    def on_tick(self, tick: Dict[str, Any]) -> None:
        """
        Feed a single tick into the candle builder.

        Expected keys in tick:
        - time: datetime
        - last_price: float
        - volume: int
        """
        tick_minute = tick["time"].minute

        # When the minute changes, emit the accumulated candle
        if self._current_minute is not None and tick_minute != self._current_minute:
            # Capture minute change immediately to prevent re-entry from concurrent ticks  
            self._current_minute = tick_minute
            if len(self.candle_builder._ticks) > 0:
                candle = self.candle_builder.build_candle()
                self.on_candle(candle)
        else:
            self._current_minute = tick_minute

        self.candle_builder.add_tick(tick)
