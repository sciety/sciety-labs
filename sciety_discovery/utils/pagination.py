from typing import NamedTuple, Optional


class UrlPaginationState(NamedTuple):
    page: int
    page_count: Optional[int] = None
    previous_page_url: Optional[str] = None
    next_page_url: Optional[str] = None


def get_page_count_for_item_count_and_items_per_page(
    item_count: int,
    items_per_page: int
) -> int:
    return max(1, (item_count + items_per_page - 1) // items_per_page)
