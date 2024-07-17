from datetime import date, datetime, timezone
from typing import Optional, Union


def parse_timestamp(timestamp_str: str) -> datetime:
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'
    return datetime.fromisoformat(timestamp_str)


def parse_timestamp_or_none(timestamp_str: Optional[str]) -> Optional[datetime]:
    if not timestamp_str:
        return None
    return parse_timestamp(timestamp_str)


def parse_date_or_none(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    return date.fromisoformat(date_str)


def get_date_as_isoformat(date_value: Optional[Union[date, datetime]]) -> Optional[str]:
    if not date_value:
        return None
    return date_value.strftime(r'%Y-%m-%d')


def get_date_as_display_format(date_value: Optional[Union[date, datetime]]) -> Optional[str]:
    if not date_value:
        return None
    return date_value.strftime(r'%b %-d, %Y')


def get_timestamp_as_isoformat(timestamp_value: Optional[Union[date, datetime]]) -> Optional[str]:
    if not timestamp_value:
        return None
    return timestamp_value.isoformat()


def get_utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_utc_timestamp_with_tzinfo(timestamp: datetime) -> datetime:
    if timestamp.tzinfo:
        return timestamp
    return timestamp.replace(tzinfo=timezone.utc)


def get_date_as_utc_timestamp(date_: date) -> datetime:
    return datetime.combine(date_, datetime.min.time(), tzinfo=timezone.utc)
