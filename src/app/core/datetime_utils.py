from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime.

    The application historically stores UTC timestamps as naive datetimes.
    Keep that database contract while avoiding deprecated datetime.utcnow().
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
