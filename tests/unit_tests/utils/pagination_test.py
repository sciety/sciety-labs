from typing import Mapping
from urllib.parse import parse_qsl, urlparse
import starlette.datastructures

from sciety_discovery.utils.pagination import (
    get_page_count_for_item_count_and_items_per_page,
    get_url_pagination_state_for_url
)


URL_WITHOUT_PAGE_PARAMETER = starlette.datastructures.URL(
    'https://example/path'
)


def _parse_query_parameters_from_url(url: str) -> Mapping[str, str]:
    query_string = urlparse(url).query
    return starlette.datastructures.MultiDict(parse_qsl(query_string))


class TestGetPageCountForItemCountAndItemsPerPage:
    def test_should_return_one_if_item_count_is_zero(self):
        assert get_page_count_for_item_count_and_items_per_page(
            item_count=0, items_per_page=10
        ) == 1

    def test_should_return_one_if_item_count_equals_items_per_page(self):
        assert get_page_count_for_item_count_and_items_per_page(
            item_count=10, items_per_page=10
        ) == 1

    def test_should_return_two_if_item_count_equals_items_per_page_plus_one(self):
        assert get_page_count_for_item_count_and_items_per_page(
            item_count=11, items_per_page=10
        ) == 2


class TestGetUrlPaginationStateForUrl:
    def test_should_not_include_previous_and_next_page_without_items_per_page(self):
        url_pagination_state = get_url_pagination_state_for_url(
            url=URL_WITHOUT_PAGE_PARAMETER,
            page=1,
            items_per_page=None,
            item_count=None
        )
        assert not url_pagination_state.previous_page_url
        assert not url_pagination_state.next_page_url

    def test_should_not_include_previous_and_next_page_if_pagination_is_disabled(self):
        url_pagination_state = get_url_pagination_state_for_url(
            url=URL_WITHOUT_PAGE_PARAMETER,
            page=1,
            items_per_page=10,
            item_count=20,
            enable_pagination=False
        )
        assert not url_pagination_state.previous_page_url
        assert not url_pagination_state.next_page_url

    def test_should_calculate_page_count_if_item_count_is_known(self):
        url_pagination_state = get_url_pagination_state_for_url(
            url=URL_WITHOUT_PAGE_PARAMETER,
            page=1,
            items_per_page=10,
            item_count=20
        )
        assert url_pagination_state.page_count == 2

    def test_should_calculate_no_previous_but_next_page_url_on_first_page(self):
        url_pagination_state = get_url_pagination_state_for_url(
            url=URL_WITHOUT_PAGE_PARAMETER,
            page=1,
            items_per_page=10,
            item_count=30
        )
        assert url_pagination_state.previous_page_url is None
        assert url_pagination_state.next_page_url is not None
        assert (
            _parse_query_parameters_from_url(url_pagination_state.next_page_url).get('page')
            == '2'
        )

    def test_should_calculate_previous_and_next_page_url(self):
        url_pagination_state = get_url_pagination_state_for_url(
            url=URL_WITHOUT_PAGE_PARAMETER,
            page=2,
            items_per_page=10,
            item_count=30
        )
        assert url_pagination_state.previous_page_url is not None
        assert url_pagination_state.next_page_url is not None
        assert (
            _parse_query_parameters_from_url(url_pagination_state.previous_page_url).get('page')
            == '1'
        )
        assert (
            _parse_query_parameters_from_url(url_pagination_state.next_page_url).get('page')
            == '3'
        )

    def test_should_calculate_previous_but_not_next_page_url_on_last_page(self):
        url_pagination_state = get_url_pagination_state_for_url(
            url=URL_WITHOUT_PAGE_PARAMETER,
            page=3,
            items_per_page=10,
            item_count=30
        )
        assert url_pagination_state.previous_page_url is not None
        assert url_pagination_state.next_page_url is None
        assert (
            _parse_query_parameters_from_url(url_pagination_state.previous_page_url).get('page')
            == '2'
        )
