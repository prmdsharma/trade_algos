"""
Lightweight trade logger backed by SQLite via SQLAlchemy.
"""

import logging
import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, Trade

logger = logging.getLogger(__name__)


class TradeLogger:
    """
    Persists completed trades to a local SQLite database.

    Usage:
        trade_logger = TradeLogger()          # creates trades.db
        trade_logger.log_entry(position)      # on entry
        trade_logger.log_exit(position, ...)  # on exit
    """

    def __init__(self, db_path: str = "trades.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"TradeLogger initialized: {db_path}")

    def log_entry(self, position: dict, timestamp: Optional[datetime.datetime] = None) -> int:
        """Record a new entry. Returns the DB row id."""
        session = self.Session()
        try:
            trade = Trade(
                signal_type=position.get("type"),
                symbol=position.get("symbol"),
                strike=position.get("strike"),
                entry_price=position.get("entry_price"),
                qty=position.get("qty"),
                
                # Extended entry fields
                entry_vix=position.get("entry_vix"),
                entry_ema9=position.get("ema9"),
                entry_ema21=position.get("ema21"),
                entry_vwap=position.get("vwap"),
                entry_spot_open=position.get("spot_open"),
                entry_spot_high=position.get("spot_high"),
                entry_spot_low=position.get("spot_low"),
                entry_spot_close=position.get("spot_close"),
                
                entry_time=timestamp or datetime.datetime.utcnow(),
            )
            session.add(trade)
            session.commit()
            logger.info(f"Trade logged (entry): id={trade.id} {trade.symbol}")
            return trade.id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log entry: {e}")
            return -1
        finally:
            session.close()

    def log_exit(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        exit_reason: str,
        timestamp: Optional[datetime.datetime] = None,
        exit_params: Optional[dict] = None,
    ) -> None:
        """Update an existing trade row with exit details."""
        session = self.Session()
        try:
            trade = session.query(Trade).filter_by(id=trade_id).first()
            if trade is None:
                logger.warning(f"Trade id={trade_id} not found for exit update.")
                return
            
            trade.exit_price = exit_price
            trade.pnl = pnl
            trade.exit_reason = exit_reason
            trade.exit_time = timestamp or datetime.datetime.utcnow()
            
            # Extended exit fields
            if exit_params:
                trade.exit_vix = exit_params.get("vix")
                trade.exit_ema9 = exit_params.get("ema9")
                trade.exit_ema21 = exit_params.get("ema21")
                trade.exit_vwap = exit_params.get("vwap")
                trade.exit_spot_open = exit_params.get("spot_open")
                trade.exit_spot_high = exit_params.get("spot_high")
                trade.exit_spot_low = exit_params.get("spot_low")
                trade.exit_spot_close = exit_params.get("spot_close")
                
            session.commit()
            logger.info(f"Trade logged (exit): id={trade_id} reason={exit_reason} pnl={pnl:.2f}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log exit: {e}")
        finally:
            session.close()
