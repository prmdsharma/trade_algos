"""
Lightweight trade logger backed by SQLite via SQLAlchemy.
"""

import logging
import datetime
from typing import Optional

from sqlalchemy import create_engine, func, and_
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

    def __init__(self, db_path: str = "database/trades.db"):
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
    def get_open_trade(self) -> Optional[dict]:
        """
        Check for a trade that was entered but not yet exited.
        Returns a dictionary compatible with TradeManager.current_position or None.
        """
        session = self.Session()
        try:
            trade = session.query(Trade).filter(Trade.exit_time == None).order_by(Trade.entry_time.desc()).first()
            if trade:
                return {
                    'db_id': trade.id,
                    'type': trade.signal_type,
                    'symbol': trade.symbol,
                    'strike': trade.strike,
                    'entry_price': trade.entry_price,
                    'qty': trade.qty,
                    # Restore spot params if available
                    'ema9': trade.entry_ema9,
                    'ema21': trade.entry_ema21,
                    'spot_open': trade.entry_spot_open,
                    'spot_high': trade.entry_spot_high,
                    'spot_low': trade.entry_spot_low,
                    'spot_close': trade.entry_spot_close,
                    'entry_time': trade.entry_time,
                }
            return None
        except Exception as e:
            logger.error(f"Failed to fetch open trade: {e}")
            return None
        finally:
            session.close()

    def get_daily_stats(self, date: datetime.date) -> dict:
        """
        Calculate daily metrics for RiskEngine recovery.
        """
        session = self.Session()
        try:
            start_of_day = datetime.datetime.combine(date, datetime.time.min)
            end_of_day = datetime.datetime.combine(date, datetime.time.max)

            # Query all trades completed today
            trades = (
                session.query(Trade)
                .filter(
                    and_(
                        Trade.exit_time >= start_of_day,
                        Trade.exit_time <= end_of_day
                    )
                )
                .order_by(Trade.exit_time.asc())
                .all()
            )

            total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
            total_trades = len(trades)
            
            # Calculate consecutive losses from the end of today's sequence
            consecutive_losses = 0
            for t in reversed(trades):
                if t.pnl is not None and t.pnl < 0:
                    consecutive_losses += 1
                else:
                    break  # Hit a win or a break in the sequence

            return {
                "daily_pnl": total_pnl,
                "trades_today": total_trades,
                "consecutive_losses": consecutive_losses
            }
        except Exception as e:
            logger.error(f"Failed to fetch daily stats: {e}")
            return {"daily_pnl": 0.0, "trades_today": 0, "consecutive_losses": 0}
        finally:
            session.close()
