"""
Tests for risk-breach auto-flattening in TradeManager.

Verifies that when the daily loss limit is breached:
1. Open positions are force-closed.
2. New entries are blocked.
3. RiskEngine accessors report the breach.
"""

from execution.trade_manager import TradeManager
from risk.risk_engine import RiskEngine


# ---------- Test doubles ----------

class DummyBroker:
    def __init__(self):
        self.ltps = {}
        self.orders = []

    def get_ltp(self, symbol: str) -> float:
        return self.ltps.get(symbol, 100.0)

    def place_order(self, symbol, qty, order_type="MARKET", transaction_type="BUY"):
        self.orders.append((symbol, qty, order_type, transaction_type))
        return "ORDER_DUMMY"


class DummyOrderManager:
    def __init__(self, broker):
        self.broker = broker

    def place_entry_order(self, symbol, qty, side):
        return self.broker.place_order(symbol, qty, "MARKET", side)

    def place_exit_order(self, symbol, qty, side):
        return self.broker.place_order(symbol, qty, "MARKET", side)


def _cfg():
    return {
        "account": {"initial_capital": 500000},
        "risk": {
            "max_trades_per_day": 4,
            "max_consecutive_losses": 2,
            "daily_loss_limit_pct": 0.03,   # 3% => Rs 15 000
            "risk_per_trade_pct": 0.01,
        },
        "trade_params": {"target_pct": 0.12, "stop_loss_pct": 0.08},
        "windows": {
            "morning_start": "09:25",
            "morning_end": "10:30",
            "afternoon_start": "13:30",
            "afternoon_end": "14:45",
        },
        "broker": {
            "sensex_symbol_root": "SENSEX",
            "exchange": "BFO",
            "product": "MIS",
        },
    }


# ---------- Tests ----------

def test_force_exit_on_loss_limit_breach():
    """
    When the risk engine's daily loss limit is already breached,
    manage_open_positions must force-close the open position.
    """
    cfg = _cfg()
    broker = DummyBroker()
    risk = RiskEngine(cfg)
    om = DummyOrderManager(broker)
    tm = TradeManager(cfg, broker, risk, om)

    symbol = tm._build_option_symbol(72000, "CE")
    broker.ltps[symbol] = 100.0

    # Manually open a position
    candle = {
        "EMA9": 101, "EMA21": 100, "VWAP": 100,
        "open": 100, "close": 72000, "low": 71900, "high": 72100,
    }
    tm.execute_entry("CE", candle)
    assert tm.current_position is not None, "Position should be open"

    # Simulate a catastrophic loss that breaches the 3% daily limit
    risk.update_metrics(-16000)  # > 15 000 limit

    assert risk.is_loss_limit_breached()
    assert not risk.can_trade()

    # manage_open_positions should now force-exit
    tm.manage_open_positions(candle)
    assert tm.current_position is None, "Position should have been force-closed"


def test_entry_blocked_after_loss_limit():
    """
    New entries must be rejected when the daily loss limit has been hit.
    """
    cfg = _cfg()
    broker = DummyBroker()
    risk = RiskEngine(cfg)
    om = DummyOrderManager(broker)
    tm = TradeManager(cfg, broker, risk, om)

    # Breach the daily loss limit before any trade
    risk.update_metrics(-16000)

    candle = {
        "EMA9": 101, "EMA21": 100, "VWAP": 100,
        "open": 100, "close": 72000, "low": 71900, "high": 72100,
    }
    tm.execute_entry("CE", candle)
    assert tm.current_position is None, "No entry should be allowed after loss limit breach"


def test_consecutive_losses_block_trading():
    """
    Trading must stop after max consecutive losses.
    """
    cfg = _cfg()
    risk = RiskEngine(cfg)

    risk.update_metrics(-100)
    risk.update_metrics(-100)
    assert not risk.can_trade()


def test_risk_engine_accessors():
    """
    Verify is_loss_limit_breached and get_daily_pnl report correctly.
    """
    cfg = _cfg()
    risk = RiskEngine(cfg)

    assert risk.get_daily_pnl() == 0.0
    assert not risk.is_loss_limit_breached()

    risk.update_metrics(-14000)
    assert risk.get_daily_pnl() == -14000
    assert not risk.is_loss_limit_breached()  # under limit

    risk.update_metrics(-1500)
    assert risk.get_daily_pnl() == -15500
    assert risk.is_loss_limit_breached()  # over limit
