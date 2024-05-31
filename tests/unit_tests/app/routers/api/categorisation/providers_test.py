from unittest.mock import AsyncMock, MagicMock

import opensearchpy
import pytest

from sciety_labs.app.routers.api.categorisation.providers import (
    ArticleDoiNotFoundError,
    AsyncOpenSearchCategoriesProvider,
    get_categorisation_response_dict_for_opensearch_document_dict
)


DOI_1 = '10.12345/test-doi-1'


@pytest.fixture(name='async_opensearch_categories_provider')
def _async_opensearch_categories_provider(
    app_providers_and_models_mock: MagicMock
) -> AsyncOpenSearchCategoriesProvider:
    return AsyncOpenSearchCategoriesProvider(
        app_providers_and_models=app_providers_and_models_mock
    )


class TestArticleDoiNotFoundError:
    def test_should_include_doi_in_str_and_repr(self):
        exception = ArticleDoiNotFoundError(article_doi=DOI_1)
        assert DOI_1 in str(exception)
        assert DOI_1 in repr(exception)


class TestGetCategorisationDictForOpensearchDocumentDict:
    def test_should_return_empty_dict_if_no_categories_are_available(self):
        categories_dict = get_categorisation_response_dict_for_opensearch_document_dict({})
        assert categories_dict == {}  # pylint: disable=use-implicit-booleaness-not-comparison

    def test_should_extract_crossref_group_title_as_categories(self):
        categories_response_dict = get_categorisation_response_dict_for_opensearch_document_dict({
            'crossref': {
                'group_title': 'Category 1'
            }
        })
        assert categories_response_dict == {
            'data': [{
                'display_name': 'Category 1',
                'type': 'category',
                'source_id': 'crossref_group_title'
            }]
        }


class TestAsyncOpenSearchCategoriesProvider:
    @pytest.mark.asyncio
    async def test_should_raise_article_doi_not_found_error(
        self,
        async_opensearch_categories_provider: AsyncOpenSearchCategoriesProvider,
        async_opensearch_client_mock: AsyncMock
    ):
        async_opensearch_client_mock.get_source.side_effect = opensearchpy.NotFoundError()
        with pytest.raises(ArticleDoiNotFoundError):
            await async_opensearch_categories_provider.get_categorisation_response_dict_by_doi(
                article_doi=DOI_1
            )
