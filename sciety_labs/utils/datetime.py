from datetime import datetime


def parse_timestamp(timestamp_str: str) -> datetime:
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'
    return datetime.fromisoformat(timestamp_str)
