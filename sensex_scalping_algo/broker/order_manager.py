"""
High-level order management built on top of a broker client.

Keeps `TradeManager` simple by hiding broker-specific details.
"""

from __future__ import annotations

from typing import Any


class OrderManager:
    """
    Thin wrapper around a broker client (e.g. KiteClientLive).

    Expected broker interface:
    - place_order(symbol_or_strike, qty, order_type=\"MARKET\", transaction_type=\"BUY\")
    """

    def __init__(self, broker: Any):
        self.broker = broker

    def place_entry_order(self, symbol: str, qty: int, side: str) -> str:
        """
        Place an entry order (BUY for CE/PE).
        """
        return self.broker.place_order(symbol, qty, "MARKET", side)

    def place_exit_order(self, symbol: str, qty: int, side: str) -> str:
        """
        Place an exit order (SELL for open positions).
        """
        return self.broker.place_order(symbol, qty, "MARKET", side)
