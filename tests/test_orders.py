from execution.trade_manager import TradeManager
from risk.risk_engine import RiskEngine
from risk.position_sizer import PositionSizer


class DummyBroker:
    def __init__(self):
        self.ltps = {}
        self.orders = []

    def get_ltp(self, symbol: str) -> float:
        return self.ltps.get(symbol, 100.0)

    def place_order(self, symbol: str, qty: int, order_type: str = "MARKET", transaction_type: str = "BUY") -> str:
        self.orders.append((symbol, qty, order_type, transaction_type))
        return "ORDER123"


class DummyOrderManager:
    def __init__(self, broker: DummyBroker):
        self.broker = broker

    def place_entry_order(self, symbol: str, qty: int, side: str):
        return self.broker.place_order(symbol, qty, "MARKET", side)

    def place_exit_order(self, symbol: str, qty: int, side: str):
        return self.broker.place_order(symbol, qty, "MARKET", side)


def make_config():
    return {
        "account": {"initial_capital": 500000},
        "risk": {
            "max_trades_per_day": 4,
            "max_consecutive_losses": 2,
            "daily_loss_limit_pct": 0.03,
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
            "api_key": "",
            "access_token": "",
            "sensex_symbol_root": "SENSEX",
            "exchange": "BFO",
            "product": "MIS",
        },
    }


def test_trade_manager_entry_and_exit_flow():
    cfg = make_config()
    broker = DummyBroker()
    risk_engine = RiskEngine(cfg)
    order_manager = DummyOrderManager(broker)
    tm = TradeManager(cfg, broker, risk_engine, order_manager)

    candle = {
        "EMA9": 101,
        "EMA21": 100,
        "VWAP": 100,
        "open": 100,
        "close": 72000,  # spot, used for strike selection
        "low": 71900,
        "high": 72100,
    }

    # Force a known LTP for the built symbol
    symbol = tm._build_option_symbol(72000, "CE")
    broker.ltps[symbol] = 100.0

    tm.execute_entry("CE", candle)
    assert tm.current_position is not None
    assert len(broker.orders) == 1  # entry

    # Now set higher premium to trigger target/exit
    broker.ltps[symbol] = 120.0
    tm.manage_open_positions(candle)
    assert tm.current_position is None
    assert len(broker.orders) == 2  # entry + exit

