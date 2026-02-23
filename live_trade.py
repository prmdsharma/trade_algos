"""
Launch live trading mode.

Uses real market data with real order execution.
USE WITH CAUTION.

Prerequisites:
  - Valid API credentials in config.yaml or as environment variables.
  - Adequate capital in the broker account.

Usage:
  python live_trade.py
"""

from core.app import run_live_trading

if __name__ == "__main__":
    run_live_trading()
