import logging
import datetime
from typing import Dict, Any, Optional

from strategy.strike_selector import StrikeSelector
from risk.position_sizer import PositionSizer
from risk.risk_engine import RiskEngine
from broker.order_manager import OrderManager
from core.utils import get_next_weekly_expiry, format_kite_expiry
from core.constants import SENSEX_SYMBOL_ROOT
from .exit_engine import ExitEngine

try:
    from database.db_manager import TradeLogger
except Exception:  # pragma: no cover
    TradeLogger = None  # type: ignore

class TradeManager:
    def __init__(self, config, broker, risk_engine: RiskEngine, order_manager: OrderManager):
        self.config = config
        self.broker = broker
        self.risk_engine = risk_engine
        self.order_manager = order_manager
        self.sizer = PositionSizer(config)
        self.exit_engine = ExitEngine(config)
        self.current_position = None
        self.logger = logging.getLogger(f"sensex_scalping.{__name__}")

        # Optional trade persistence
        try:
            self._trade_logger = TradeLogger() if TradeLogger else None
        except Exception:
            self._trade_logger = None

    # ---- Liquidity validation (spec requirement) ----

    def _validate_liquidity(self, symbol: str) -> bool:
        """
        Basic liquidity gate before entry.

        In live mode this should check bid-ask spread and/or volume.
        For the stub it always passes because we don't have L2 data.
        """
        try:
            ltp = self.broker.get_ltp(symbol)
            if ltp <= 0:
                self.logger.warning(f"Liquidity check FAILED for {symbol}: LTP={ltp}")
                return False
            self.logger.info(f"Liquidity check PASSED for {symbol}: LTP={ltp}")
            return True
        except Exception as e:
            self.logger.warning(f"Liquidity check SKIPPED for {symbol}: {e}")
            # In backtest mode, allow trade even if LTP fetch fails
            return True

    def _build_option_symbol(self, strike: int, option_type: str, as_of: Optional[datetime.date] = None) -> str:
        """
        Build a Sensex weekly option symbol from strike and type.
        """
        root = self.config.get("broker", {}).get("sensex_symbol_root", SENSEX_SYMBOL_ROOT)
        expiry = get_next_weekly_expiry(as_of=as_of)
        expiry_code = format_kite_expiry(expiry)
        return f"{root}{expiry_code}{strike}{option_type}"

    def execute_entry(self, signal_type, candle):
        if self.current_position:
            return  # Already in a trade

        # Spec: must not open new trades when risk limits are breached
        if not self.risk_engine.can_trade():
            self.logger.warning("Entry blocked: risk limits breached.")
            return

        # [cite_start]        # 1. Select Strike (ATM)
        spot_price = candle['close']
        strike = StrikeSelector.get_atm_strike(spot_price)

        # Extract date from candle for correct expiry calculation
        candle_date = None
        if 'time' in candle:
            ts = candle['time']
            if hasattr(ts, 'date'):
                candle_date = ts.date()

        # 2. Get Premium Price (Option LTP if available)
        option_symbol = self._build_option_symbol(strike, signal_type, as_of=candle_date)

        # Spec: validate liquidity before placing an order
        if not self._validate_liquidity(option_symbol):
            self.logger.warning(f"Skipping entry due to liquidity for {option_symbol}")
            return

        try:
            premium_price = self.broker.get_ltp(option_symbol)
        except Exception:
            # Fallback: simple proxy based on spot (for dev/backtest)
            premium_price = spot_price * 0.005

        # [cite_start]3. Size Position [cite: 31]
        qty = self.sizer.calculate_qty(premium_price)
        if qty <= 0:
            self.logger.warning(f"Calculated qty is 0 for {option_symbol}. Skipping.")
            return

        # 4. Place Order (via OrderManager/broker) using option symbol
        order_id = self.order_manager.place_entry_order(option_symbol, qty, "BUY")

        self.current_position = {
            'id': order_id,
            'type': signal_type,
            'entry_price': premium_price,
            'qty': qty,
            'strike': strike,
            'symbol': option_symbol,
            
            # Extended params for reporting
            'ema9': candle.get('EMA9'),
            'ema21': candle.get('EMA21'),
            'vwap': candle.get('VWAP'),
            'spot_open': candle.get('open'),
            'spot_high': candle.get('high'),
            'spot_low': candle.get('low'),
            'spot_close': candle.get('close'),
        }

        # Persist entry to database
        if self._trade_logger:
            db_id = self._trade_logger.log_entry(self.current_position, timestamp=candle.get('time'))
            self.current_position['db_id'] = db_id

        self.logger.info(f"ENTRY EXECUTED: {signal_type} {option_symbol} @ {premium_price}")

    def manage_open_positions(self, candle):
        if not self.current_position:
            return

        # Spec: auto-flatten when daily loss limit is breached
        if not self.risk_engine.can_trade():
            self.logger.warning("Daily loss limit breached – force-closing position.")
            self._force_exit(candle, reason="Daily Loss Limit")
            return

        # Refresh option premium for exit checks
        symbol = self.current_position['symbol']
        try:
            current_premium = self.broker.get_ltp(symbol)
        except Exception:
            # Fallback to using spot close as proxy (consistent with entry fallback)
            current_premium = candle['close'] * 0.005

        # Use option premium in exit-engine context
        candle_for_exit = dict(candle)
        candle_for_exit['close'] = current_premium

        # Provide real-time visibility for the open trade
        entry_price = self.current_position['entry_price']
        pnl = (current_premium - entry_price) * self.current_position['qty']
        pct_change = ((current_premium - entry_price) / entry_price) * 100
        self.logger.info(f"TRADING: {symbol} | Entry: {entry_price:.2f} | LTP: {current_premium:.2f} | PnL: {pnl:+.2f} ({pct_change:+.2f}%)")

        # [cite_start]Check exit conditions [cite: 26]
        should_exit, reason = self.exit_engine.check_exit(self.current_position, candle_for_exit)

        if should_exit:
            # Determine exit price using option premium
            exit_price = current_premium
            entry_price = self.current_position['entry_price']
            qty = self.current_position['qty']

            # Simple PnL calculation per unit * quantity
            pnl = (exit_price - entry_price) * qty

            # Place exit order (SELL) using the stored option symbol
            symbol = self.current_position['symbol']
            self.order_manager.place_exit_order(symbol, qty, "SELL")

            self.logger.info(f"EXIT EXECUTED: {reason} | {symbol} | PnL: {pnl:.2f}")

            # Update risk metrics with realized PnL
            self.risk_engine.update_metrics(pnl)

            # Persist exit to database
            if self._trade_logger and 'db_id' in self.current_position:
                exit_params = {
                    'ema9': candle.get('EMA9'),
                    'ema21': candle.get('EMA21'),
                    'vwap': candle.get('VWAP'),
                    'spot_open': candle.get('open'),
                    'spot_high': candle.get('high'),
                    'spot_low': candle.get('low'),
                    'spot_close': candle.get('close'),
                }
                self._trade_logger.log_exit(
                    self.current_position['db_id'], 
                    exit_price, 
                    pnl, 
                    reason,
                    timestamp=candle.get('time'),
                    exit_params=exit_params
                )

            # Clear open position
            self.current_position = None

    # ---- Force exit helper (used by daily-loss flattening) ----

    def _force_exit(self, candle, reason: str = "Forced"):
        """Close the current position immediately, regardless of exit-engine signals."""
        if not self.current_position:
            return

        symbol = self.current_position['symbol']
        qty = self.current_position['qty']
        entry_price = self.current_position['entry_price']

        try:
            exit_price = self.broker.get_ltp(symbol)
        except Exception:
            exit_price = candle['close'] * 0.005

        pnl = (exit_price - entry_price) * qty

        self.order_manager.place_exit_order(symbol, qty, "SELL")
        self.logger.info(f"FORCE EXIT: {reason} | {symbol} | PnL: {pnl:.2f}")

        self.risk_engine.update_metrics(pnl)

        # Persist exit to database
        if self._trade_logger and 'db_id' in self.current_position:
            exit_params = {
                'ema9': candle.get('EMA9'),
                'ema21': candle.get('EMA21'),
                'vwap': candle.get('VWAP'),
                'spot_open': candle.get('open'),
                'spot_high': candle.get('high'),
                'spot_low': candle.get('low'),
                'spot_close': candle.get('close'),
            }
            self._trade_logger.log_exit(
                self.current_position['db_id'], 
                exit_price, 
                pnl, 
                reason,
                timestamp=candle.get('time'),
                exit_params=exit_params
            )

        self.current_position = None
