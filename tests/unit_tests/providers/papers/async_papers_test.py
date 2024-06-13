from datetime import date
import logging
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from sciety_labs.app.routers.api.papers.typing import PaperSearchResponseDict
from sciety_labs.providers.papers.async_papers import (
    DEFAULT_PROVIDER_PAPER_FIELDS,
    AsyncPapersProvider,
    get_search_result_list_for_paper_search_response_dict,
    get_search_result_list_items_for_paper_search_response_dict
)


LOGGER = logging.getLogger(__name__)


DOI_1 = '10.12345/doi_1'


PAPER_SEARCH_RESPONSE_DICT_1: PaperSearchResponseDict = {
    'data': [{
        'id': DOI_1,
        'type': 'paper',
        'attributes': {
            'doi': DOI_1
        }
    }]
}


@pytest.fixture(name='response_mock')
def _response_mock() -> AsyncMock:
    response_mock = AsyncMock(aiohttp.ClientResponse, name='response_mock')
    return response_mock


@pytest.fixture(name='response_context_manager_mock')
def _response_context_manager_mock(response_mock: AsyncMock) -> MagicMock:
    response_context_manager_mock = MagicMock(name='request_context_manager_mock')
    response_context_manager_mock.__aenter__.return_value = response_mock
    return response_context_manager_mock


@pytest.fixture(name='client_session_mock')
def _client_session_mock(
    response_context_manager_mock: MagicMock
) -> AsyncMock:
    client_session_mock = AsyncMock(aiohttp.ClientSession, name='client_session_mock')
    client_session_mock.get.return_value = response_context_manager_mock
    return client_session_mock


@pytest.fixture(name='client_session_get_mock')
def _client_session_get_mock(client_session_mock: AsyncMock) -> AsyncMock:
    return client_session_mock.get


@pytest.fixture(name='async_papers_provider')
def _async_papers_provider(
    client_session_mock: AsyncMock
) -> AsyncPapersProvider:
    return AsyncPapersProvider(
        client_session=client_session_mock
    )


class TestGetSearchResultListItemsForPaperSearchResponseDict:
    def test_should_return_empty_list_if_search_response_is_empty(self):
        items = get_search_result_list_items_for_paper_search_response_dict({
            'data': []
        })
        assert not items

    def test_should_parse_minimal_search_response_with_doi(self):
        items = get_search_result_list_items_for_paper_search_response_dict({
            'data': [{
                'id': 'some_id',
                'type': 'paper',
                'attributes': {
                    'doi': DOI_1
                }
            }]
        })
        assert len(items) == 1
        item = items[0]
        assert item.article_doi == DOI_1
        assert item.article_meta.article_doi == DOI_1

    def test_should_parse_search_response_with_doi_and_title(self):
        items = get_search_result_list_items_for_paper_search_response_dict({
            'data': [{
                'id': 'some_id',
                'type': 'paper',
                'attributes': {
                    'doi': DOI_1,
                    'title': 'Title 1',
                    'publication_date': '2001-02-03'
                }
            }]
        })
        assert len(items) == 1
        item = items[0]
        assert item.article_doi == DOI_1
        assert item.article_meta.article_doi == DOI_1
        assert item.article_meta.article_title == 'Title 1'
        assert item.article_meta.published_date == date.fromisoformat('2001-02-03')


class TestAsyncPapersProvider:
    @pytest.mark.asyncio
    async def test_should_pass_cateogry_to_client_session_get_as_params(
        self,
        async_papers_provider: AsyncPapersProvider,
        client_session_get_mock: AsyncMock
    ):
        search_result_list = await (
            async_papers_provider.get_preprints_for_category_search_results_list(
                category='Category 1'
            )
        )
        assert search_result_list
        _, kwargs = client_session_get_mock.call_args
        assert kwargs['params']['filter[category]'] == 'Category 1'
        assert set(kwargs['params']['fields[paper]'].split(',')) == DEFAULT_PROVIDER_PAPER_FIELDS

    @pytest.mark.asyncio
    async def test_should_return_parsed_response_json(
        self,
        async_papers_provider: AsyncPapersProvider,
        response_mock: AsyncMock
    ):
        response_mock.json.return_value = PAPER_SEARCH_RESPONSE_DICT_1
        search_result_list = await (
            async_papers_provider.get_preprints_for_category_search_results_list(
                category='Category 1'
            )
        )
        assert search_result_list == get_search_result_list_for_paper_search_response_dict(
            PAPER_SEARCH_RESPONSE_DICT_1
        )
