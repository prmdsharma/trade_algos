"""
Tests for multi-broker support: broker factory + ICICI client utilities.
"""

import pytest

from broker.broker_base import BrokerBase
from broker.broker_factory import create_broker
from broker.icici_client import ICICIClientLive


# ---------------------------------------------------------------------------
# BrokerBase contract
# ---------------------------------------------------------------------------

def test_broker_base_cannot_be_instantiated():
    """BrokerBase is abstract and should not be directly instantiated."""
    with pytest.raises(TypeError):
        BrokerBase()  # type: ignore


# ---------------------------------------------------------------------------
# Broker factory
# ---------------------------------------------------------------------------

import os

def _base_config(**overrides):
    # Resolve the CSV path relative to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(project_root, "data", "backtest_data", "backtest_prices.csv")

    cfg = {
        "account": {"initial_capital": 100000},
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
        "broker": {"name": "kite"},
        "backtest": {"csv_path": csv_path},
    }
    cfg["broker"].update(overrides)
    return cfg


def test_factory_returns_stub_for_kite(tmp_path):
    """create_broker with mode='stub' should return KiteClientStub."""
    from broker.kite_client import KiteClientStub

    # Create a minimal CSV so the stub can load it
    csv_file = tmp_path / "test_prices.csv"
    csv_file.write_text("time,open,high,low,close,volume\n2024-01-01 09:30:00,100,101,99,100.5,1000\n")

    config = _base_config(name="kite")
    config["backtest"]["csv_path"] = str(csv_file)
    broker = create_broker(config, mode="stub")
    assert isinstance(broker, KiteClientStub)
    assert isinstance(broker, BrokerBase)


def test_factory_raises_on_unknown_broker():
    """Factory should raise ValueError for an unsupported broker name."""
    config = _base_config(name="unknown_broker")
    with pytest.raises(ValueError, match="Unknown broker"):
        create_broker(config, mode="live")


# ---------------------------------------------------------------------------
# ICICI symbol parser
# ---------------------------------------------------------------------------

def test_parse_symbol_ce():
    """_parse_symbol should correctly parse a CE option symbol."""
    root, strike, option_type, expiry = ICICIClientLive._parse_symbol(
        "SENSEX26FEB2672000CE"
    )
    assert root == "BSESEN"
    assert strike == 72000
    assert option_type == "call"
    assert expiry == "2026-02-26"


def test_parse_symbol_pe():
    """_parse_symbol should correctly parse a PE option symbol."""
    root, strike, option_type, expiry = ICICIClientLive._parse_symbol(
        "SENSEX26MAR2665000PE"
    )
    assert root == "BSESEN"
    assert strike == 65000
    assert option_type == "put"
    assert expiry == "2026-03-26"


def test_parse_symbol_different_months():
    """Verify month mapping works for various months."""
    _, _, _, expiry_jan = ICICIClientLive._parse_symbol("SENSEX26JAN50000CE")
    _, _, _, expiry_dec = ICICIClientLive._parse_symbol("SENSEX26DEC80000PE")

    assert "-01-" in expiry_jan
    assert "-12-" in expiry_dec
