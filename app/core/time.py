from datetime import datetime, timezone
from zoneinfo import ZoneInfo


INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def assume_india_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=INDIA_TIMEZONE)
    return value


def to_utc(value: datetime) -> datetime:
    return assume_india_timezone(value).astimezone(timezone.utc)
