import re


def remove_markup(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text)
