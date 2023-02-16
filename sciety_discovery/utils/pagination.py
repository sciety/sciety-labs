import logging
from typing import NamedTuple, Optional

import starlette.datastructures


LOGGER = logging.getLogger(__name__)


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


def get_url_pagination_state_for_url(
    url: starlette.datastructures.URL,
    page: int,
    items_per_page: Optional[int] = None,
    item_count: Optional[int] = None,
    enable_pagination: bool = True
) -> UrlPaginationState:
    if not items_per_page or not enable_pagination:
        return UrlPaginationState(page=page)
    page_count: Optional[int] = None
    previous_page_url: Optional[str] = None
    next_page_url: Optional[str] = None
    assert item_count is not None
    page_count = get_page_count_for_item_count_and_items_per_page(
        item_count=item_count, items_per_page=items_per_page
    )
    if page > 1:
        previous_page_url = str(url.include_query_params(
            page=page - 1
        ))
    if page < page_count:
        next_page_url = str(url.include_query_params(
            page=page + 1
        ))
        LOGGER.info('next_page_url: %r', next_page_url)
    else:
        LOGGER.info('no more items past this page')
        page_count = page
    return UrlPaginationState(
        page=page,
        page_count=page_count,
        previous_page_url=previous_page_url,
        next_page_url=next_page_url
    )
