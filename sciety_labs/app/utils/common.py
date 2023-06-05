from sciety_labs.utils.text import remove_markup


def get_page_title(text: str) -> str:
    return remove_markup(text)
