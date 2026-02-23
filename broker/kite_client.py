"""
Broker client implementations for Sensex scalping.

`KiteClientStub` is used by default in `main.py` as a safe placeholder.
For real live trading, implement and use `KiteClientLive`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .broker_base import BrokerBase

try:
    # Optional import – only needed for live trading
    from kiteconnect import KiteConnect
except ImportError:  # pragma: no cover - handled via requirements
    KiteConnect = None  # type: ignore

class KiteClientStub(BrokerBase):
    """
    Simple stub so the rest of the system can be developed and tested
    without hitting the real broker.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Backtest CSV path can be overridden via config['backtest']['csv_path']
        backtest_cfg = config.get("backtest", {})
        csv_path = backtest_cfg.get(
            "csv_path", "data/backtest_data/backtest_prices.csv"
        )

        self._csv_path = Path(csv_path)
        if not self._csv_path.exists():
            raise FileNotFoundError(
                f"Backtest CSV not found at {self._csv_path}. "
                "Update config.backtest.csv_path or add the file."
            )

        # Expect columns: time, open, high, low, close, volume
        df = pd.read_csv(self._csv_path)
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])

        required_cols = {"open", "high", "low", "close", "volume"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(
                f"Backtest CSV missing required columns: {', '.join(sorted(missing))}"
            )

        self._data = df.sort_values("time").reset_index(drop=True)
        self._idx: int = 0
        self._option_cache: Dict[str, pd.DataFrame] = {}
        self._options_dir = self._csv_path.parent / "options"

    def get_latest_candle(self) -> pd.DataFrame:
        """
        Return historical candles up to the current index as a DataFrame.
        """
        if self._idx >= len(self._data):
            raise StopIteration("Backtest data exhausted.")

        self._idx += 1
        return self._data.iloc[: self._idx].copy()

    def _get_option_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Lazy load option data from CSV."""
        if symbol in self._option_cache:
            return self._option_cache[symbol]

        csv_path = self._options_dir / f"{symbol}.csv"
        if csv_path.exists():
            print(f"Loading option data for {symbol}...")
            df = pd.read_csv(csv_path)
            df["time"] = pd.to_datetime(df["time"])
            self._option_cache[symbol] = df
            return df
        return None

    def place_order(self, symbol: str, qty: int, order_type: str = "MARKET", transaction_type: str = "BUY") -> str:
        """Mock order placement."""
        print(f"[MOCK ORDER] {transaction_type} {qty} @ {symbol} ({order_type})")
        return "MOCK_ORDER_ID"

    def get_ltp(self, instrument: str) -> float:
        """
        Fetch LTP. For options, looks up historical data at the current backtest timestamp.
        """
        if self._idx == 0:
            raise ValueError("No candle data consumed yet.")

        current_ts = self._data.iloc[self._idx - 1]["time"]

        if "CE" in instrument or "PE" in instrument:
            opt_df = self._get_option_data(instrument)
            if opt_df is not None:
                # Find matching timestamp in option data
                match = opt_df[opt_df["time"] == current_ts]
                if not match.empty:
                    return float(match.iloc[0]["close"])
                else:
                    # If match not found, log and fallback
                    print(f"Warning: No historical data for {instrument} at {current_ts}")

            raise ValueError(f"Historical data for {instrument} at {current_ts} not found.")

        return float(self._data.iloc[self._idx - 1]["close"])

class KiteClientLive(BrokerBase):
    """
    Minimal live Kite client wrapper.

    Reads API credentials from environment variables first, then from config:
    - KITE_API_KEY / KITE_ACCESS_TOKEN

    Config fallback (optional):
    broker:
      api_key: "..."
      access_token: "..."
    """

    def __init__(self, config: Dict[str, Any]):
        if KiteConnect is None:
            raise ImportError("kiteconnect is not installed. Add it to requirements and pip install it.")

        broker_cfg = config.get("broker", {})
        api_key = os.environ.get("KITE_API_KEY") or broker_cfg.get("api_key")
        access_token = os.environ.get("KITE_ACCESS_TOKEN") or broker_cfg.get("access_token")

        if not api_key or not access_token:
            raise ValueError("Kite API credentials missing. Set KITE_API_KEY/KITE_ACCESS_TOKEN or config['broker'].")

        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        self.config = config

    def place_order(self, symbol: str, qty: int, order_type: str = "MARKET", transaction_type: str = "BUY") -> str:
        """
        Place a simple intraday market order.

        NOTE: `symbol` should be a full tradingsymbol (e.g. SENSEX24FEB60000CE).
        You may want to build this symbol from strike/option type in TradeManager.
        """
        order = self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=self.kite.EXCHANGE_BFO,
            tradingsymbol=symbol,
            transaction_type=transaction_type,
            quantity=qty,
            product=self.kite.PRODUCT_MIS,
            order_type=order_type,
        )
        return str(order)

    def get_ltp(self, symbol: str) -> float:
        exchange = self.config.get("broker", {}).get("exchange", "BFO")
        data = self.kite.ltp([f"{exchange}:{symbol}"])
        key = next(iter(data.keys()))
        return data[key]["last_price"]


class KiteClientPaper(KiteClientLive):
    """
    Paper trading client: real market data, simulated orders.

    Inherits `get_ltp` from KiteClientLive (real prices) but overrides
    `place_order` to only log the trade without hitting the broker.
    """

    _next_id: int = 1

    def place_order(
        self,
        symbol: str,
        qty: int,
        order_type: str = "MARKET",
        transaction_type: str = "BUY",
    ) -> str:
        order_id = f"PAPER_{KiteClientPaper._next_id}"
        KiteClientPaper._next_id += 1

        # Fetch the real LTP so the paper fill is at a realistic price
        try:
            ltp = self.get_ltp(symbol)
        except Exception:
            ltp = 0.0

        print(
            f"[PAPER ORDER] {transaction_type} {qty}x {symbol} "
            f"@ {ltp:.2f} ({order_type}) → {order_id}"
        )
        return order_id
