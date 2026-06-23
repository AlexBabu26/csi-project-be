"""IST (Asia/Kolkata) datetime helpers used across the CSI backend."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    """Return the current naive datetime in IST for DateTime columns without timezone."""
    return datetime.now(IST).replace(tzinfo=None)


def now_ist_aware() -> datetime:
    """Return the current timezone-aware datetime in IST."""
    return datetime.now(IST)


def today_ist() -> date:
    """Return the current calendar date in IST."""
    return datetime.now(IST).date()


def current_year_ist() -> int:
    """Return the current calendar year in IST."""
    return today_ist().year


def format_timestamp_ist(dt: datetime | None = None, fmt: str = "%Y%m%d-%H%M%S") -> str:
    """Format a datetime as an IST timestamp string (defaults to now)."""
    value = dt or now_ist()
    if value.tzinfo is not None:
        value = value.astimezone(IST).replace(tzinfo=None)
    return value.strftime(fmt)
