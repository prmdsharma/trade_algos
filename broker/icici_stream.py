"""
ICICI Direct Breeze WebSocket streaming adapter.

Wires Breeze websocket ticks to the WebSocketHandlerSkeleton, which
converts them into 1-minute candles.
"""

from __future__ import annotations

import os
import logging
import pandas as pd
from typing import Any, Dict

logger = logging.getLogger(f"sensex_scalping.{__name__}")

try:
    from breeze_connect import BreezeConnect  # type: ignore
except ImportError:  # pragma: no cover
    BreezeConnect = None  # type: ignore


def create_icici_stream(config: Dict[str, Any], ws_handler: Any):
    """
    Create and configure a Breeze websocket connection.

    Parameters
    ----------
    config : dict
        Full app config (needs broker.icici_* credentials and
        broker.ticker_tokens for instrument subscription).
    ws_handler : WebSocketHandlerSkeleton
        Handler whose .on_tick() will be called with each tick.

    Returns
    -------
    BreezeConnect
        The connected Breeze instance.
    """
    if BreezeConnect is None:
        raise ImportError(
            "breeze-connect is not installed. Run: pip install breeze-connect"
        )

    broker_cfg = config.get("broker", {})
    api_key = os.environ.get("ICICI_API_KEY") or broker_cfg.get("icici_api_key", "")
    secret_key = os.environ.get("ICICI_SECRET_KEY") or broker_cfg.get("icici_secret_key", "")
    session_token = os.environ.get("ICICI_SESSION_TOKEN") or broker_cfg.get("icici_session_token", "")

    breeze = BreezeConnect(api_key=api_key)
    breeze.generate_session(api_secret=secret_key, session_token=session_token)

    def on_ticks(tick_data: Dict[str, Any]):
        """Adapter: transform Breeze tick format to our handler format."""
        try:
            # Breeze live ticks use different keys than historical/quotes
            tick = {
                "last_price": float(tick_data.get("last", 0)),
                "time": pd.to_datetime(tick_data.get("ltt")),
                "volume": int(tick_data.get("ttq", 0)) if tick_data.get("ttq") else 0,
            }
            
            # Log the tick for visibility (DEBUG only to avoid noise)
            logger.debug(f"Tick received: {tick['time']} | Price: {tick['last_price']} | Vol: {tick['volume']}")
            
            # Skeleton expects a single tick dict
            ws_handler.on_tick(tick)
        except Exception as e:
            logger.error(f"Error processing ICICI tick: {e}")

    # Assign the callback
    breeze.on_ticks = on_ticks

    # Start the websocket connection
    breeze.ws_connect()
    
    # Wait for connection to stabilize
    import time
    time.sleep(5)

    # Subscribe to the configured stock
    stock_code = broker_cfg.get("icici_stock_code", "BSESEN")
    exchange_code = broker_cfg.get("icici_exchange_code", "BSE")

    breeze.subscribe_feeds(
        exchange_code=exchange_code,
        stock_code=stock_code,
    )

    logger.info(f"ICICI Breeze stream subscribed and connected: {exchange_code}:{stock_code}")
    return breeze
