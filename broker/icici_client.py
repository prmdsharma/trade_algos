"""
ICICI Direct Breeze broker client implementations.

`ICICIClientLive`  — real orders + real market data via breeze-connect.
`ICICIClientPaper` — real market data, simulated orders.

Requires: pip install breeze-connect
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict

from .broker_base import BrokerBase

try:
    from breeze_connect import BreezeConnect  # type: ignore
except ImportError:  # pragma: no cover
    BreezeConnect = None  # type: ignore

logger = logging.getLogger(f"sensex_scalping.{__name__}")


class ICICIClientLive(BrokerBase):
    """
    Live ICICI Direct client using the Breeze API.

    Credentials (env vars preferred, config fallback):
        ICICI_API_KEY, ICICI_SECRET_KEY, ICICI_SESSION_TOKEN
    """

    def __init__(self, config: Dict[str, Any]):
        if BreezeConnect is None:
            raise ImportError(
                "breeze-connect is not installed. Run: pip install breeze-connect"
            )

        broker_cfg = config.get("broker", {})
        api_key = os.environ.get("ICICI_API_KEY") or broker_cfg.get("icici_api_key", "")
        secret_key = os.environ.get("ICICI_SECRET_KEY") or broker_cfg.get("icici_secret_key", "")
        session_token = os.environ.get("ICICI_SESSION_TOKEN") or broker_cfg.get("icici_session_token", "")

        if not api_key or not secret_key:
            raise ValueError(
                "ICICI API credentials missing. "
                "Set ICICI_API_KEY / ICICI_SECRET_KEY env vars or config['broker']."
            )

        self.breeze = BreezeConnect(api_key=api_key)
        self.breeze.generate_session(
            api_secret=secret_key, session_token=session_token
        )
        self.config = config
        logger.info("ICICIClientLive initialized.")

    def place_order(
        self,
        symbol: str,
        qty: int,
        order_type: str = "MARKET",
        transaction_type: str = "BUY",
    ) -> str:
        """
        Place an intraday market order on BSE for Sensex options.

        Symbol mapping note:
            Our system uses Kite-style symbols (e.g. SENSEX26FEB72000CE).
            Breeze requires stock_code + strike + option_type separately.
            The _parse_symbol helper extracts these.
        """
        stock_code, strike_price, option_type, expiry = self._parse_symbol(symbol)

        # Map our transaction_type to Breeze action
        action = "buy" if transaction_type.upper() == "BUY" else "sell"

        response = self.breeze.place_order(
            stock_code=stock_code,
            exchange_code="BFO",
            product="Options",
            action=action,
            order_type=order_type.lower(),
            stoploss="",
            quantity=str(qty),
            price="",
            validity="day",
            disclosed_quantity="0",
            expiry_date=expiry,
            right=option_type.lower(),  # "call" or "put"
            strike_price=str(strike_price),
        )

        order_id = str(response.get("Success", {}).get("order_id", "ICICI_UNKNOWN"))
        logger.info(
            f"[ICICI ORDER] {action.upper()} {qty}x {symbol} → {order_id}"
        )
        return order_id

    def get_ltp(self, symbol: str) -> float:
        """
        Fetch the last traded price via Breeze quotes API.
        """
        stock_code, strike_price, option_type, expiry = self._parse_symbol(symbol)

        quotes = self.breeze.get_quotes(
            stock_code=stock_code,
            exchange_code="BFO",
            product_type="Options",
            right=option_type.lower(),
            strike_price=str(strike_price),
            expiry_date=expiry,
        )

        if quotes and "Success" in quotes:
            data = quotes["Success"]
            if isinstance(data, list) and len(data) > 0:
                return float(data[0].get("ltp", 0.0))
        raise ValueError(f"Could not fetch LTP for {symbol}: {quotes}")

    @staticmethod
    def _parse_symbol(symbol: str):
        """
        Parse a Kite-style option symbol into Breeze components.

        Example: SENSEX26FEB72000CE
        Returns: ("SENSEX", 72000, "call", "2026-02-26")

        This is an approximation — adjust the parsing logic to match
        actual symbol formats from your broker.
        """
        # Strip the root
        root = "SENSEX"
        stock_code = "BSESEN"
        remainder = symbol.replace(root, "")  # e.g. "26FEB72000CE"

        # Option type is the last 2 chars
        opt_type_code = remainder[-2:]  # CE or PE
        option_type = "call" if opt_type_code == "CE" else "put"

        # Strike is the numeric part before the option type
        num_part = remainder[:-2]  # e.g. "26FEB72000"

        # Extract expiry (first 5 chars: YYMM format e.g. "26FEB")
        expiry_code = num_part[:5]  # "26FEB"
        strike_price = int(num_part[5:])  # 72000

        # Build ISO date for expiry (approximate — use actual expiry calendar)
        month_map = {
            "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
            "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
            "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
        }
        yy = expiry_code[:2]
        mon = expiry_code[2:5].upper()
        month_num = month_map.get(mon, "01")
        # Use last day of month as a rough expiry placeholder
        expiry = f"20{yy}-{month_num}-28"

        return stock_code, strike_price, option_type, expiry


class ICICIClientPaper(ICICIClientLive):
    """
    Paper trading with ICICI: real market data, simulated orders.
    """

    _next_id: int = 1

    def place_order(
        self,
        symbol: str,
        qty: int,
        order_type: str = "MARKET",
        transaction_type: str = "BUY",
    ) -> str:
        order_id = f"ICICI_PAPER_{ICICIClientPaper._next_id}"
        ICICIClientPaper._next_id += 1

        try:
            ltp = self.get_ltp(symbol)
        except Exception:
            ltp = 0.0

        print(
            f"[ICICI PAPER] {transaction_type} {qty}x {symbol} "
            f"@ {ltp:.2f} ({order_type}) → {order_id}"
        )
        return order_id
