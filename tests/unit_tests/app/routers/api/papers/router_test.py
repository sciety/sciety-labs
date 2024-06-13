import logging
from typing import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sciety_labs.app.routers.api.papers.providers import (
    DoiNotFoundError,
    AsyncOpenSearchPapersProvider
)
import sciety_labs.app.routers.api.papers.router as router_module
from sciety_labs.app.routers.api.papers.router import (
    create_api_papers_router,
    get_invalid_api_fields_json_response_dict,
    get_doi_not_found_error_json_response_dict
)
from sciety_labs.app.routers.api.papers.typing import (
    PaperSearchResponseDict,
    CategorisationResponseDict
)
from sciety_labs.app.routers.api.utils.validation import InvalidApiFieldsError
from sciety_labs.providers.opensearch.utils import OpenSearchFilterParameters


LOGGER = logging.getLogger(__name__)


DOI_1 = '10.12345/test-doi-1'

INVALID_DOI_1 = 'invalid-doi-1'

CATEGORISATION_RESPONSE_DICT_1: CategorisationResponseDict = {
    'data': [{
        'type': 'category',
        'id': 'Category 1',
        'attributes': {
            'display_name': 'Category 1',
            'source_id': 'Source 1'
        }
    }]
}


PAPER_SEARCH_RESPONSE_DICT_1: PaperSearchResponseDict = {
    'data': [{
        'type': 'paper',
        'id': DOI_1,
        'attributes': {
            'doi': DOI_1
        }
    }]
}


@pytest.fixture(name='async_opensearch_papers_provider_class_mock', autouse=True)
def _async_opensearch_papers_provider_class_mock(
) -> Iterator[MagicMock]:
    with patch.object(router_module, 'AsyncOpenSearchPapersProvider') as mock:
        mock.return_value = AsyncMock(AsyncOpenSearchPapersProvider)
        yield mock


@pytest.fixture(name='async_opensearch_papers_provider_mock', autouse=True)
def _async_opensearch_papers_provider_mock(
    async_opensearch_papers_provider_class_mock: MagicMock
) -> AsyncMock:
    return async_opensearch_papers_provider_class_mock.return_value


@pytest.fixture(name='get_classification_list_response_dict_mock', autouse=True)
def _get_classification_list_response_dict_mock(
    async_opensearch_papers_provider_mock: AsyncMock
) -> AsyncMock:
    return (
        async_opensearch_papers_provider_mock
        .get_classification_list_response_dict
    )


@pytest.fixture(name='get_classification_response_dict_by_doi_mock', autouse=True)
def _get_classification_response_dict_by_doi_mock(
    async_opensearch_papers_provider_mock: AsyncMock
) -> AsyncMock:
    return (
        async_opensearch_papers_provider_mock
        .get_classificiation_response_dict_by_doi
    )


@pytest.fixture(name='get_paper_search_response_dict_mock', autouse=True)
def _get_paper_search_response_dict_mock(
    async_opensearch_papers_provider_mock: AsyncMock
) -> AsyncMock:
    return (
        async_opensearch_papers_provider_mock
        .get_paper_search_response_dict
    )


@pytest.fixture(name='test_client')
def _test_client(app_providers_and_models_mock: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(create_api_papers_router(
        app_providers_and_models=app_providers_and_models_mock
    ))
    return TestClient(app)


class TestGetNotFoundErrorJsonResponseDict:
    def test_should_return_json_dict_for_exception(self):
        exception = DoiNotFoundError(
            DOI_1
        )
        assert get_doi_not_found_error_json_response_dict(exception) == {
            'errors': [{
                'title': 'Invalid DOI',
                'detail': f'DOI not found: {DOI_1}',
                'status': '404'
            }]
        }


class TestPapersApiRouterClassificationList:
    def test_should_provide_classification_list_response(
        self,
        get_classification_list_response_dict_mock: AsyncMock,
        test_client: TestClient
    ):
        get_classification_list_response_dict_mock.return_value = CATEGORISATION_RESPONSE_DICT_1
        response = test_client.get(
            '/papers/v1/preprints/classifications'
        )
        response.raise_for_status()
        assert response.json() == CATEGORISATION_RESPONSE_DICT_1

    def test_should_pass_evaluated_only_filter_to_provider(
        self,
        get_classification_list_response_dict_mock: AsyncMock,
        test_client: TestClient
    ):
        get_classification_list_response_dict_mock.return_value = (
            PAPER_SEARCH_RESPONSE_DICT_1
        )
        test_client.get(
            '/papers/v1/preprints/classifications',
            params={'filter[evaluated_only]': 'true'}
        )
        _, kwargs = get_classification_list_response_dict_mock.call_args
        filter_parameters: OpenSearchFilterParameters = kwargs['filter_parameters']
        assert filter_parameters.evaluated_only


class TestPapersApiRouterClassificationListByDoi:
    def test_should_provide_classification_response(
        self,
        get_classification_response_dict_by_doi_mock: AsyncMock,
        test_client: TestClient
    ):
        get_classification_response_dict_by_doi_mock.return_value = CATEGORISATION_RESPONSE_DICT_1
        response = test_client.get(
            f'/papers/v1/preprints/classifications/by/doi/{DOI_1}'
        )
        response.raise_for_status()
        assert response.json() == CATEGORISATION_RESPONSE_DICT_1

    def test_should_return_404_if_not_found(
        self,
        get_classification_response_dict_by_doi_mock: AsyncMock,
        test_client: TestClient
    ):
        exception = DoiNotFoundError(
            DOI_1
        )
        get_classification_response_dict_by_doi_mock.side_effect = exception
        response = test_client.get(
            f'/papers/v1/preprints/classifications/by/doi/{DOI_1}'
        )
        assert response.status_code == 404
        assert response.json() == get_doi_not_found_error_json_response_dict(exception)


class TestPapersApiRouterPreprints:
    def test_should_return_response_from_provider(
        self,
        get_paper_search_response_dict_mock: AsyncMock,
        test_client: TestClient
    ):
        get_paper_search_response_dict_mock.return_value = (
            PAPER_SEARCH_RESPONSE_DICT_1
        )
        response = test_client.get(
            '/papers/v1/preprints',
            params={'filter[category]': 'Category 1'}
        )
        response.raise_for_status()
        assert response.json() == PAPER_SEARCH_RESPONSE_DICT_1

    def test_should_pass_evaluated_only_and_category_filter_to_provider(
        self,
        get_paper_search_response_dict_mock: AsyncMock,
        test_client: TestClient
    ):
        get_paper_search_response_dict_mock.return_value = (
            PAPER_SEARCH_RESPONSE_DICT_1
        )
        test_client.get(
            '/papers/v1/preprints',
            params={'filter[category]': 'Category 1', 'filter[evaluated_only]': 'true'}
        )
        _, kwargs = get_paper_search_response_dict_mock.call_args
        filter_parameters: OpenSearchFilterParameters = kwargs['filter_parameters']
        assert filter_parameters.category == 'Category 1'
        assert filter_parameters.evaluated_only

    def test_should_pass_api_fields_to_provider(
        self,
        get_paper_search_response_dict_mock: AsyncMock,
        test_client: TestClient
    ):
        get_paper_search_response_dict_mock.return_value = (
            PAPER_SEARCH_RESPONSE_DICT_1
        )
        test_client.get(
            '/papers/v1/preprints',
            params={'filter[category]': 'Category 1', 'fields[paper]': 'doi,title'}
        )
        get_paper_search_response_dict_mock.assert_called()
        _, kwargs = get_paper_search_response_dict_mock.call_args
        assert kwargs['paper_fields_set'] == {'doi', 'title'}

    def test_should_raise_error_for_invalid_field_name(
        self,
        get_paper_search_response_dict_mock: AsyncMock,
        test_client: TestClient
    ):
        get_paper_search_response_dict_mock.return_value = (
            PAPER_SEARCH_RESPONSE_DICT_1
        )
        response = test_client.get(
            '/papers/v1/preprints',
            params={'filter[category]': 'Category 1', 'fields[paper]': 'doi,invalid_1'}
        )
        assert response.status_code == 400
        response_json = response.json()
        LOGGER.debug('response_json: %r', response_json)
        assert response_json == get_invalid_api_fields_json_response_dict(
            InvalidApiFieldsError({'invalid_1'})
        )