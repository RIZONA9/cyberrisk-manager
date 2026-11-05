from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return UTC without an offset for consistent SQLite storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
