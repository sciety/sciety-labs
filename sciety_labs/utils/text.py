import re
from typing import Optional, Sequence


def remove_markup(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text)


def remove_markup_or_none(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return re.sub(r'<[^>]+>', '', text)


def parse_csv(text: str, delimiter: str = ',') -> Sequence[str]:
    if not text:
        return []
    return text.split(sep=delimiter)
