from datetime import datetime, timezone


def now() -> datetime:
    """Return the current time as timezone-aware UTC."""
    return datetime.now(timezone.utc)