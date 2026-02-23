from risk.risk_engine import RiskEngine


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


def test_risk_engine_limits():
    cfg = make_config()
    engine = RiskEngine(cfg)

    # Under limits initially
    assert engine.can_trade()

    # Hit max trades per day
    for _ in range(cfg["risk"]["max_trades_per_day"]):
        engine.update_metrics(0)
    assert not engine.can_trade()

