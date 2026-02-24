"""
Execution layer for the Sensex 1-min scalping algo.

This package is responsible for:
- Translating trade signals into executable orders (`TradeManager`)
- Applying exit rules (targets, SL, opposite signal) via `ExitEngine`
"""

from .trade_manager import TradeManager
from .exit_engine import ExitEngine

__all__ = ["TradeManager", "ExitEngine"]
