"""
Shared utility functions.
"""

import datetime as _dt
from typing import Tuple, Optional

from .constants import TIME_FORMAT_HM


def parse_time_hm(value: str) -> _dt.time:
    """Parse a HH:MM time string into a time object."""
    return _dt.datetime.strptime(value, TIME_FORMAT_HM).time()


def get_today_date() -> _dt.date:
    """Return today's date (exchange calendar naive)."""
    return _dt.date.today()


def compute_pct_change(old: float, new: float) -> float:
    """Return percentage change between two prices."""
    if old == 0:
        return 0.0
    return (new - old) / old


def get_next_weekly_expiry(as_of: Optional[_dt.date] = None) -> _dt.date:
    """
    Return the next weekly expiry date (Thursday) from a given date.

    NOTE: This is a generic helper; check exchange rules and holidays
    for production use.
    """
    if as_of is None:
        as_of = get_today_date()

    # Monday=0, Sunday=6; Thursday=3
    days_ahead = (3 - as_of.weekday()) % 7
    days_ahead = 7 if days_ahead == 0 else days_ahead
    return as_of + _dt.timedelta(days=days_ahead)


def format_kite_expiry(expiry: _dt.date) -> str:
    """
    Format expiry as YYMON for Kite-style symbols, e.g. 2024-02-29 -> 24FEB.
    """
    year_short = str(expiry.year % 100).zfill(2)
    month_str = expiry.strftime("%b").upper()
    return f"{year_short}{month_str}"

