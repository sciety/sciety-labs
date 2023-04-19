from datetime import date, datetime
from typing import Optional, Union


def parse_timestamp(timestamp_str: str) -> datetime:
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'
    return datetime.fromisoformat(timestamp_str)


def get_date_as_isoformat(date_value: Union[date, datetime]) -> Optional[str]:
    if not date_value:
        return None
    return date_value.strftime(r'%Y-%m-%d')


def get_date_as_display_format(date_value: Union[date, datetime]) -> Optional[str]:
    if not date_value:
        return None
    return date_value.strftime(r'%b %-d, %Y')


def get_timestamp_as_isoformat(timestamp_value: Union[date, datetime]) -> Optional[str]:
    if not timestamp_value:
        return None
    return timestamp_value.isoformat()
