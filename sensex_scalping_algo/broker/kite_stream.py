"""
KiteTicker (websocket) wiring helpers.

This module connects the broker's live tick stream to the generic
`WebSocketHandlerSkeleton` which aggregates ticks into 1‑min candles.
"""

from typing import Any, Dict, List

try:
    from kiteconnect import KiteTicker  # type: ignore
except ImportError:  # pragma: no cover
    KiteTicker = None  # type: ignore


def create_kite_ticker(config: Dict[str, Any], ws_handler) -> Any:
    """
    Create and configure a KiteTicker instance wired to `ws_handler`.

    Expected config structure:

    broker:
      api_key: "..."
      access_token: "..."
      ticker_tokens:
        - 256265   # Example instrument token (e.g. NIFTY spot) – replace with Sensex
    """
    if KiteTicker is None:
        raise ImportError("kiteconnect is not installed. Install it to use live KiteTicker streams.")

    broker_cfg = config.get("broker", {})
    api_key = broker_cfg.get("api_key")
    access_token = broker_cfg.get("access_token")
    tokens: List[int] = broker_cfg.get("ticker_tokens", [])

    if not api_key or not access_token:
        raise ValueError("broker.api_key / broker.access_token must be set in config for KiteTicker.")

    if not tokens:
        raise ValueError("broker.ticker_tokens must contain at least one instrument token for streaming.")

    ticker = KiteTicker(api_key, access_token)

    def on_ticks(ws, ticks):
        # Each `tick` is a dict from Kite; map to the structure expected
        # by WebSocketHandlerSkeleton.on_tick
        for t in ticks:
            ws_handler.on_tick(
                {
                    "time": t["timestamp"],
                    "last_price": t["last_price"],
                    "volume": t.get("volume", 0),
                }
            )

    def on_connect(ws, response):
        # Subscribe to configured tokens in FULL mode so we get prices & timestamp
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)

    ticker.on_ticks = on_ticks
    ticker.on_connect = on_connect
    return ticker

