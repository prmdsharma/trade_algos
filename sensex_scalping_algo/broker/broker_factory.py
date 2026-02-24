"""
Broker factory: create the right broker client from config.

Usage:
    broker = create_broker(config, mode="paper")
"""

from typing import Any, Dict

from .broker_base import BrokerBase


def create_broker(config: Dict[str, Any], mode: str = "live") -> BrokerBase:
    """
    Instantiate a broker client based on config and mode.

    Parameters
    ----------
    config : dict
        Full application config (must contain ``broker.name``).
    mode : str
        One of ``"live"``, ``"paper"``, or ``"stub"``.

    Returns
    -------
    BrokerBase
        Ready-to-use broker client.
    """
    broker_name = config.get("broker", {}).get("name", "kite").lower()

    if broker_name == "kite":
        return _create_kite(config, mode)
    elif broker_name == "icici":
        return _create_icici(config, mode)
    else:
        raise ValueError(
            f"Unknown broker '{broker_name}'. Supported: 'kite', 'icici'."
        )


def _create_kite(config: Dict[str, Any], mode: str) -> BrokerBase:
    from .kite_client import KiteClientStub, KiteClientLive, KiteClientPaper

    if mode == "stub":
        return KiteClientStub(config)
    elif mode == "paper":
        return KiteClientPaper(config)
    else:
        return KiteClientLive(config)


def _create_icici(config: Dict[str, Any], mode: str) -> BrokerBase:
    if mode == "stub":
        from .kite_client import KiteClientStub
        return KiteClientStub(config)
    elif mode == "paper":
        from .icici_client import ICICIClientPaper
        return ICICIClientPaper(config)
    else:
        from .icici_client import ICICIClientLive
        return ICICIClientLive(config)
