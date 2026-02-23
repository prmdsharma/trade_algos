"""
Abstract base class for all broker clients.

Every broker implementation (Kite, ICICI Breeze, etc.) must extend
this class and implement the two core methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BrokerBase(ABC):
    """
    Minimal interface that the trading system requires from any broker.

    Subclasses:
        - KiteClientLive / KiteClientPaper / KiteClientStub
        - ICICIClientLive / ICICIClientPaper
    """

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        qty: int,
        order_type: str = "MARKET",
        transaction_type: str = "BUY",
    ) -> str:
        """Place an order and return a broker-assigned order ID string."""
        ...

    @abstractmethod
    def get_ltp(self, symbol: str) -> float:
        """Return the last traded price for the given instrument symbol."""
        ...
