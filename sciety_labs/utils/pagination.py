import logging
import itertools
from typing import Any, Iterable, NamedTuple, Optional, TypeVar

import starlette.datastructures

from sciety_labs.utils.typing import SupportsNext


LOGGER = logging.getLogger(__name__)


T = TypeVar('T')


class UrlPaginationParameters(NamedTuple):
    page: int
    items_per_page: int
    enable_pagination: bool = True


class UrlPaginationState(NamedTuple):
    page: int
    is_empty: Optional[bool] = None
    page_count: Optional[int] = None
    previous_page_url: Optional[str] = None
    next_page_url: Optional[str] = None


def get_page_count_for_item_count_and_items_per_page(
    item_count: int,
    items_per_page: int
) -> int:
    return max(1, (item_count + items_per_page - 1) // items_per_page)


def get_page_iterable(
    iterable: Iterable[T],
    page: int,
    items_per_page: Optional[int] = None
) -> Iterable[T]:
    if not items_per_page:
        return iterable
    assert page >= 1
    return itertools.islice(
        iterable,
        (page - 1) * items_per_page,  # start
        page * items_per_page  # stop
    )


def get_url_pagination_state_for_url(  # pylint: disable=too-many-arguments
    url: starlette.datastructures.URL,
    page: int,
    is_this_page_empty: bool = False,
    items_per_page: Optional[int] = None,
    item_count: Optional[int] = None,
    remaining_item_iterable: Optional[SupportsNext[Any]] = None,
    enable_pagination: bool = True
) -> UrlPaginationState:
    if not items_per_page or not enable_pagination:
        return UrlPaginationState(page=page)
    page_count: Optional[int] = None
    previous_page_url: Optional[str] = None
    next_page_url: Optional[str] = None
    if item_count is None and remaining_item_iterable is None:
        raise AssertionError('either item_count or remaining_item_iterable must be specified')
    if page > 1:
        previous_page_url = str(url.include_query_params(
            page=page - 1
        ))
    has_next_page = False
    if item_count is not None:
        page_count = get_page_count_for_item_count_and_items_per_page(
            item_count=item_count, items_per_page=items_per_page
        )
        if page < page_count:
            has_next_page = True
    elif (
        remaining_item_iterable is not None
        and next(remaining_item_iterable, None) is not None
    ):
        has_next_page = True
    if has_next_page:
        next_page_url = str(url.include_query_params(
            page=page + 1
        ))
        LOGGER.info('next_page_url: %r', next_page_url)
    else:
        LOGGER.info('no more items past this page')
        page_count = page
    return UrlPaginationState(
        page=page,
        is_empty=is_this_page_empty and page == 1,
        page_count=page_count,
        previous_page_url=previous_page_url,
        next_page_url=next_page_url
    )
