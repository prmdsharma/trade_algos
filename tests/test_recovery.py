import datetime
import pytest
from unittest.mock import MagicMock
from execution.trade_manager import TradeManager
from risk.risk_engine import RiskEngine
from database.db_manager import TradeLogger

@pytest.fixture
def full_config():
    return {
        "broker": {"name": "stub"},
        "risk": {
            "max_trades_per_day": 5, 
            "max_consecutive_losses": 3, 
            "daily_loss_limit_pct": 0.02,
            "risk_per_trade_pct": 0.01
        },
        "account": {"initial_capital": 100000},
        "trade_params": {"stop_loss_pct": 0.08, "target_pct": 0.12},
        "windows": {
            "morning_start": "09:20",
            "morning_end": "10:30",
            "afternoon_start": "13:30",
            "afternoon_end": "14:45"
        }
    }

def test_full_state_recovery(full_config):
    # Setup
    broker = MagicMock()
    risk_engine = RiskEngine(full_config)
    order_manager = MagicMock()
    
    # Mock TradeLogger
    logger_mock = MagicMock(spec=TradeLogger)
    
    # 1. Mock daily stats: 2 trades, -1000 pnl, 1 consecutive loss
    logger_mock.get_daily_stats.return_value = {
        "daily_pnl": -1000.0,
        "trades_today": 2,
        "consecutive_losses": 1
    }
    
    # 2. Mock open trade
    logger_mock.get_open_trade.return_value = {
        "db_id": 123,
        "symbol": "SENSEX_EXP_STRIKE_CE",
        "entry_price": 400.0,
        "qty": 10,
        "type": "CE"
    }

    # Initialize TradeManager (should trigger recovery)
    tm = TradeManager(full_config, broker, risk_engine, order_manager, trade_logger=logger_mock)
    
    # Verify RiskEngine state
    assert risk_engine.daily_pnl == -1000.0
    assert risk_engine.trades_today == 2
    assert risk_engine.consecutive_losses == 1
    
    # Verify Open Position state
    assert tm.current_position is not None
    assert tm.current_position["db_id"] == 123
    assert tm.current_position["symbol"] == "SENSEX_EXP_STRIKE_CE"

def test_risk_limits_after_recovery(full_config):
    # Setup with tight limits
    config = full_config.copy()
    config["risk"]["daily_loss_limit_pct"] = 0.01 # 1% = 1000
    
    broker = MagicMock()
    risk_engine = RiskEngine(config)
    order_manager = MagicMock()
    
    logger_mock = MagicMock(spec=TradeLogger)
    
    # Recover state that already hits the loss limit
    logger_mock.get_daily_stats.return_value = {
        "daily_pnl": -1000.0, # Loss limit reached
        "trades_today": 2,
        "consecutive_losses": 2
    }
    logger_mock.get_open_trade.return_value = None

    tm = TradeManager(config, broker, risk_engine, order_manager, trade_logger=logger_mock)
    
    # Verify risk engine blocks further trading
    assert risk_engine.can_trade() is False
