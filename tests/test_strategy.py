import pandas as pd

from strategy.signal_engine import SignalEngine


def test_signal_engine_ce_and_pe_basic():
    engine = SignalEngine()

    # Bullish setup for CE
    candle_ce = {
        "EMA9": 101,
        "EMA21": 100,
        "VWAP": 100,
        "open": 100,
        "close": 102,
        "low": 100,
        "high": 103,
    }
    assert engine.analyze(candle_ce) == "CE"

    # Bearish setup for PE
    candle_pe = {
        "EMA9": 99,
        "EMA21": 100,
        "VWAP": 100,
        "open": 100,
        "close": 98,
        "low": 97,
        "high": 100,
    }
    assert engine.analyze(candle_pe) == "PE"

