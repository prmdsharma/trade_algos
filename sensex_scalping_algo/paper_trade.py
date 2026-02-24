"""
Launch paper trading mode.

Uses real Kite market data with simulated order execution.
No real orders are placed — all trades are logged with [PAPER] prefix.

Prerequisites:
  export KITE_API_KEY="your_api_key"
  export KITE_ACCESS_TOKEN="your_access_token"

  # Also update config.yaml:
  #   broker.ticker_tokens: [<sensex_instrument_token>]

Usage:
  python paper_trade.py
"""

from core.app import run_paper_trading

if __name__ == "__main__":
    run_paper_trading()
