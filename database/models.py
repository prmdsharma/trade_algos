"""
SQLAlchemy models for trade persistence.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()


class Trade(Base):
    """Records a single completed trade (entry + exit)."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_time = Column(DateTime, default=datetime.datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    signal_type = Column(String(4))       # CE or PE
    symbol = Column(String(50))           # e.g. SENSEX26FEB72000CE
    strike = Column(Integer)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    qty = Column(Integer)
    
    # Entry Condition Params
    entry_vix = Column(Float, nullable=True)
    entry_ema9 = Column(Float, nullable=True)
    entry_ema21 = Column(Float, nullable=True)
    entry_vwap = Column(Float, nullable=True)
    entry_spot_open = Column(Float, nullable=True)
    entry_spot_high = Column(Float, nullable=True)
    entry_spot_low = Column(Float, nullable=True)
    entry_spot_close = Column(Float, nullable=True)
    
    # Exit Params
    exit_vix = Column(Float, nullable=True)
    exit_ema9 = Column(Float, nullable=True)
    exit_ema21 = Column(Float, nullable=True)
    exit_vwap = Column(Float, nullable=True)
    exit_spot_open = Column(Float, nullable=True)
    exit_spot_high = Column(Float, nullable=True)
    exit_spot_low = Column(Float, nullable=True)
    exit_spot_close = Column(Float, nullable=True)
    
    pnl = Column(Float, nullable=True)
    exit_reason = Column(String(30), nullable=True)
