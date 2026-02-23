import time
from typing import Dict, Any, List

import pandas as pd

from core.config_loader import load_config
from core.logger import setup_logger
from broker.broker_factory import create_broker
from broker.order_manager import OrderManager
from broker.websocket_handler import WebSocketHandlerSkeleton
from strategy.indicators import IndicatorEngine
from strategy.signal_engine import SignalEngine
from risk.risk_engine import RiskEngine
from execution.trade_manager import TradeManager


def _create_stream(config, ws_handler):
    """
    Create the appropriate WebSocket stream based on broker.name in config.

    Returns a ticker/stream object with a .connect() method (or equivalent).
    """
    broker_name = config.get("broker", {}).get("name", "kite").lower()

    if broker_name == "kite":
        from broker.kite_stream import create_kite_ticker
        return create_kite_ticker(config, ws_handler)
    elif broker_name == "icici":
        from broker.icici_stream import create_icici_stream
        return create_icici_stream(config, ws_handler)
    else:
        raise ValueError(f"No stream handler for broker '{broker_name}'.")


def _build_on_candle_pipeline(config, broker, logger):
    """
    Build the shared on_candle pipeline used by both live and paper modes.

    Returns (on_candle callback, trade_manager, risk_engine).
    """
    risk_engine = RiskEngine(config)
    indicators = IndicatorEngine()
    signal_engine = SignalEngine()
    order_manager = OrderManager(broker)
    trade_manager = TradeManager(config, broker, risk_engine, order_manager)

    candles_history: List[Dict[str, Any]] = []

    def on_candle(candle: Dict[str, Any]) -> None:
        """Called on every completed 1-min candle from the websocket layer."""
        try:
            risk_engine.ensure_current_day()

            candles_history.append(candle)
            df = pd.DataFrame(candles_history)

            if not risk_engine.is_trading_window_open():
                return

            enriched_row = indicators.calculate(df)
            trade_manager.manage_open_positions(enriched_row)

            if not risk_engine.can_trade():
                logger.warning("Risk limits breached. No new entries for the day.")
                return

            signal = signal_engine.analyze(enriched_row)

            if signal:
                trade_manager.execute_entry(signal, enriched_row)
            else:
                # Provide visibility when waiting
                if not trade_manager.current_position:
                    logger.info(f"Signal Search: Spot={candle['close']:.2f} | EMA9={enriched_row['EMA9']:.2f} | EMA21={enriched_row['EMA21']:.2f} | VWAP={enriched_row['VWAP']:.2f} | Waiting for entry...")

        except Exception as e:
            logger.error(f"Error in on_candle pipeline: {e}")

    return on_candle, trade_manager, risk_engine


def build_live_on_candle_handler(config_path: str = "config.yaml"):
    """
    Create an `on_candle` callback and WebSocket stream for live trading.

    Broker is selected from config['broker']['name'] (kite or icici).
    """
    config = load_config(config_path)
    logger = setup_logger()

    broker = create_broker(config, mode="live")

    on_candle, trade_manager, risk_engine = _build_on_candle_pipeline(
        config, broker, logger
    )

    ws_handler = WebSocketHandlerSkeleton(on_candle)
    ticker = _create_stream(config, ws_handler)

    return config, on_candle, ws_handler, ticker


def build_paper_trading_handler(config_path: str = "config.yaml"):
    """
    Paper trading mode: real market data, simulated order execution.

    Broker is selected from config['broker']['name'] (kite or icici).
    """
    config = load_config(config_path)
    logger = setup_logger()

    broker = create_broker(config, mode="paper")

    on_candle, trade_manager, risk_engine = _build_on_candle_pipeline(
        config, broker, logger
    )

    ws_handler = WebSocketHandlerSkeleton(on_candle)
    ticker = _create_stream(config, ws_handler)

    return config, on_candle, ws_handler, ticker


def run_paper_trading(config_path: str = "config.yaml"):
    """Launch paper trading: connect to stream and start processing."""
    config, on_candle, ws_handler, ticker = build_paper_trading_handler(config_path)
    logger = setup_logger()
    broker_name = config.get("broker", {}).get("name", "kite").upper()
    logger.info(f"=== PAPER TRADING MODE ({broker_name}) — no real orders ===")
    logger.info("Press Ctrl+C to stop.")

    # Kite ticker uses .connect(threaded=True), Breeze stream is already connected
    if hasattr(ticker, "connect"):
        ticker.connect(threaded=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Paper trading stopped by user.")


def main_stub_loop():
    """
    Backtest engine: replays CSV candles through the full trading pipeline.

    - Uses candle timestamps for trading window / EOD checks (no wall-clock).
    - Processes all candles without sleeping.
    - Prints a backtest results summary at the end.
    """
    config = load_config("config.yaml")
    logger = setup_logger()

    broker = create_broker(config, mode="stub")
    risk_engine = RiskEngine(config)
    indicators = IndicatorEngine()
    signal_engine = SignalEngine()
    order_manager = OrderManager(broker)
    trade_manager = TradeManager(config, broker, risk_engine, order_manager)

    logger.info("=" * 50)
    logger.info("BACKTEST STARTED")
    logger.info("=" * 50)

    last_enriched = None
    total_candles = 0
    trades_taken = 0

    while True:
        try:
            tick_data = broker.get_latest_candle()
            total_candles += 1

            # Extract candle time for deterministic window checks
            last_row = tick_data.iloc[-1]
            candle_time = None
            candle_date = None
            if "time" in last_row.index:
                candle_ts = last_row["time"]
                if hasattr(candle_ts, "time"):
                    candle_time = candle_ts.time()
                if hasattr(candle_ts, "date"):
                    candle_date = candle_ts.date()

            # Ensure day change is handled (resets risk engine)
            risk_engine.ensure_current_day(date_override=candle_date)

            # Use candle time instead of wall clock
            if candle_time and not risk_engine.is_trading_window_open(candle_time):
                continue

            enriched_data = indicators.calculate(tick_data)

            # Carry candle time into the enriched dict for ExitEngine
            if candle_time:
                enriched_data["time"] = candle_ts

            last_enriched = enriched_data

            # Manage open positions (handles force-exit on risk breach)
            trade_manager.manage_open_positions(enriched_data)

            if not risk_engine.can_trade():
                # We still want to see the candles to trigger day changes/exits
                pass

            signal = signal_engine.analyze(enriched_data)

            if signal:
                prev_trades = risk_engine.trades_today
                trade_manager.execute_entry(signal, enriched_data)
                if risk_engine.trades_today > prev_trades:
                    trades_taken += 1

        except StopIteration:
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Backtest Error: {e}")

    # Flatten any open position at end of data
    if trade_manager.current_position and last_enriched is not None:
        logger.info("End of data — flattening open position.")
        trade_manager._force_exit(last_enriched, reason="End of Data")

    # ---- Results Summary ----
    daily_pnl = risk_engine.get_daily_pnl()
    total_trades = risk_engine.trades_today
    wins = sum(1 for _ in [] if True)  # placeholder — derive from trade_logger if available

    logger.info("")
    logger.info("=" * 50)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 50)
    logger.info(f"  Candles processed : {total_candles}")
    logger.info(f"  Total trades      : {total_trades}")
    logger.info(f"  Net P&L           : ₹{daily_pnl:,.2f}")
    logger.info(f"  Capital           : ₹{config['account']['initial_capital']:,}")
    if config["account"]["initial_capital"] > 0:
        ret_pct = (daily_pnl / config["account"]["initial_capital"]) * 100
        logger.info(f"  Return            : {ret_pct:+.2f}%")
    logger.info("=" * 50)
