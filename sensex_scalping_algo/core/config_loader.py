import os
import yaml
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


class ConfigError(Exception):
    """Raised when required config keys are missing or invalid."""


def _validate_config(cfg: dict) -> dict:
    required_top = ["account", "risk", "trade_params", "windows", "broker"]
    for key in required_top:
        if key not in cfg:
            raise ConfigError(f"Missing top-level config section: '{key}'")

    # Override or fill broker credentials from environment variables if not in config
    broker = cfg.get("broker", {})

    # ICICI Credentials
    if not broker.get("icici_api_key"):
        broker["icici_api_key"] = os.environ.get("ICICI_API_KEY", "")
    if not broker.get("icici_secret_key"):
        broker["icici_secret_key"] = os.environ.get("ICICI_SECRET_KEY", "")
    if not broker.get("icici_session_token"):
        broker["icici_session_token"] = os.environ.get("ICICI_SESSION_TOKEN", "")

    # Kite Credentials (for backward compatibility / Zerodha)
    if not broker.get("api_key"):
        broker["api_key"] = os.environ.get("KITE_API_KEY", "")
    if not broker.get("access_token"):
        broker["access_token"] = os.environ.get("KITE_ACCESS_TOKEN", "")

    if "initial_capital" not in cfg["account"]:
        raise ConfigError("account.initial_capital is required")

    for rk in ["max_trades_per_day", "max_consecutive_losses", "daily_loss_limit_pct", "risk_per_trade_pct"]:
        if rk not in cfg["risk"]:
            raise ConfigError(f"risk.{rk} is required")

    for tk in ["target_pct", "stop_loss_pct"]:
        if tk not in cfg["trade_params"]:
            raise ConfigError(f"trade_params.{tk} is required")

    for wk in ["morning_start", "morning_end", "afternoon_start", "afternoon_end"]:
        if wk not in cfg["windows"]:
            raise ConfigError(f"windows.{wk} is required")

    return cfg


def load_config(path: str = "config.yaml") -> dict:
    if not os.path.exists(path):
        # Allow running without config.yaml if all params are set via env or defaults
        # For now, we still expect config.yaml for non-credential params
        raise ConfigError(f"Config file not found: {path}")

    with open(path, "r") as file:
        raw = yaml.safe_load(file)
    return _validate_config(raw or {})
