"""
Time helpers — IST conversion and formatting.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def format_ist(dt: datetime | None) -> str:
    """Format a UTC datetime to IST string."""
    if dt is None:
        return "N/A"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ist_dt = dt.astimezone(IST)
    return ist_dt.strftime("%d %b %Y, %I:%M %p IST")


def format_ist_from_timestamp(ts: int | float | str) -> str:
    """Format a Unix timestamp (ms or s) or ISO string to IST."""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return ts
    elif isinstance(ts, (int, float)):
        # If timestamp is in milliseconds (>1e12), convert to seconds
        if ts > 1e12:
            ts = ts / 1000
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    else:
        return str(ts)

    return format_ist(dt)


def now_ist() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)
