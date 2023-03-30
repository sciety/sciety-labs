import re
from typing import Optional


def remove_markup(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text)


def remove_markup_or_none(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return re.sub(r'<[^>]+>', '', text)
