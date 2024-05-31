from typing import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sciety_labs.app.routers.api.categorisation.providers import (
    ArticleDoiNotFoundError,
    AsyncOpenSearchCategoriesProvider
)
import sciety_labs.app.routers.api.categorisation.router as router_module
from sciety_labs.app.routers.api.categorisation.router import (
    create_api_categorisation_router,
    get_not_found_error_json_response_dict
)
from sciety_labs.app.routers.api.categorisation.typing import CategorisationResponseDict


DOI_1 = '10.12345/test-doi-1'

INVALID_DOI_1 = 'invalid-doi-1'

CATEGORISATION_RESPONSE_DICT_1: CategorisationResponseDict = {
    'data': [{
        'source_id': 'Source 1',
        'type': 'category',
        'display_name': 'Category 1'
    }]
}


@pytest.fixture(name='async_opensearch_categories_provider_class_mock', autouse=True)
def _async_opensearch_categories_provider_class_mock(
) -> Iterator[MagicMock]:
    with patch.object(router_module, 'AsyncOpenSearchCategoriesProvider') as mock:
        mock.return_value = AsyncMock(AsyncOpenSearchCategoriesProvider)
        yield mock


@pytest.fixture(name='async_opensearch_categories_provider_mock', autouse=True)
def _async_opensearch_categories_provider_mock(
    async_opensearch_categories_provider_class_mock: MagicMock
) -> AsyncMock:
    return async_opensearch_categories_provider_class_mock.return_value


@pytest.fixture(name='get_categorisation_response_dict_by_doi_mock', autouse=True)
def _get_categorisation_response_dict_by_doi_mock(
    async_opensearch_categories_provider_mock: AsyncMock
) -> AsyncMock:
    return (
        async_opensearch_categories_provider_mock
        .get_categorisation_response_dict_by_doi
    )


@pytest.fixture(name='test_client')
def _test_client(app_providers_and_models_mock: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(create_api_categorisation_router(
        app_providers_and_models=app_providers_and_models_mock
    ))
    return TestClient(app)


class TestGetNotFoundErrorJsonResponseDict:
    def test_should_return_json_dict_for_exception(self):
        exception = ArticleDoiNotFoundError(
            DOI_1
        )
        assert get_not_found_error_json_response_dict(exception) == {
            'errors': [{
                'title': 'Invalid DOI',
                'detail': f'DOI not found: {DOI_1}',
                'status': '404'
            }]
        }


class TestCategorisationApiRouter:
    def test_should_provide_categorisation_response(
        self,
        get_categorisation_response_dict_by_doi_mock: AsyncMock,
        test_client: TestClient
    ):
        get_categorisation_response_dict_by_doi_mock.return_value = CATEGORISATION_RESPONSE_DICT_1
        response = test_client.get(
            '/categorisation/v1/categories/by/doi',
            params={'article_doi': DOI_1}
        )
        response.raise_for_status()
        assert response.json() == CATEGORISATION_RESPONSE_DICT_1

    def test_should_return_404_if_not_found(
        self,
        get_categorisation_response_dict_by_doi_mock: AsyncMock,
        test_client: TestClient
    ):
        exception = ArticleDoiNotFoundError(
            DOI_1
        )
        get_categorisation_response_dict_by_doi_mock.side_effect = exception
        response = test_client.get(
            '/categorisation/v1/categories/by/doi',
            params={'article_doi': DOI_1}
        )
        assert response.status_code == 404
        assert response.json() == get_not_found_error_json_response_dict(exception)
