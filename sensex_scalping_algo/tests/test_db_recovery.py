import os
import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Trade
from database.db_manager import TradeLogger
from risk.risk_engine import RiskEngine
from execution.trade_manager import TradeManager
from unittest.mock import MagicMock

@pytest.fixture
def db_setup():
    db_path = "test_trades.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    logger = TradeLogger(db_path=db_path)
    yield logger
    
    if os.path.exists(db_path):
        os.remove(db_path)

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

def test_actual_db_recovery(db_setup, full_config):
    logger = db_setup
    today = datetime.date.today()
    
    # 1. Simulate a previous run that crashed with an open trade and some history
    # Log a completed loss first
    trade1_id = logger.log_entry({
        "type": "PE", "symbol": "SX_OLD_PE", "strike": 72000, "entry_price": 100, "qty": 10
    }, timestamp=datetime.datetime.now() - datetime.timedelta(minutes=30))
    logger.log_exit(trade1_id, 90, -100, "Stop Loss", timestamp=datetime.datetime.now() - datetime.timedelta(minutes=25))
    
    # Log an still-open trade (this is the one that needs recovery)
    open_trade_pos = {
        "type": "CE", "symbol": "SX_ACTIVE_CE", "strike": 72500, "entry_price": 200, "qty": 20
    }
    logger.log_entry(open_trade_pos, timestamp=datetime.datetime.now() - datetime.timedelta(minutes=5))
    
    # 2. Start a fresh TradeManager (mimicking a restart)
    broker = MagicMock()
    risk_engine = RiskEngine(full_config)
    order_manager = MagicMock()
    
    # This call triggers recover_state()
    tm = TradeManager(full_config, broker, risk_engine, order_manager, trade_logger=logger)
    
    # 3. Assertions
    # Risk metrics should have recovered from the one closed trade (trade1)
    assert risk_engine.trades_today == 1
    assert risk_engine.daily_pnl == -100.0
    assert risk_engine.consecutive_losses == 1
    
    # Open position should be restored
    assert tm.current_position is not None
    assert tm.current_position['symbol'] == "SX_ACTIVE_CE"
    assert tm.current_position['qty'] == 20
    assert tm.current_position['entry_price'] == 200
    assert 'db_id' in tm.current_position
    
    # visibility flag should be True
    assert tm._first_run_after_recovery is True

    # Simulate First Candle - should force logging and clear flag
    candle = {
        'time': datetime.datetime.now(),
        'open': 82000, 'high': 82100, 'low': 81900, 'close': 82050,
        'EMA9': 82020, 'EMA21': 82010
    }
    broker.get_ltp.return_value = 210.0 # Current premium
    
    # This should call manage_open_positions and use the flag
    tm.manage_open_positions(candle)
    
    # flag should be cleared
    assert tm._first_run_after_recovery is False
    
    print("\nSUCCESS: Database-backed recovery and visibility verified.")
