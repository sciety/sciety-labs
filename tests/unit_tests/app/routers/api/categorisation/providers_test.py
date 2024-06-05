from unittest.mock import AsyncMock, MagicMock

import opensearchpy
import pytest

from sciety_labs.app.routers.api.categorisation.providers import (
    ArticleDoiNotFoundError,
    AsyncOpenSearchCategoriesProvider,
    get_article_response_dict_for_opensearch_document_dict,
    get_article_search_response_dict_for_opensearch_search_response_dict,
    get_categorisation_response_dict_for_opensearch_aggregations_response_dict,
    get_categorisation_response_dict_for_opensearch_document_dict
)
from sciety_labs.providers.opensearch.typing import OpenSearchSearchResultDict


DOI_1 = '10.12345/test-doi-1'

DUMMY_BIORXIV_DOI_1 = '10.1101/dummy-biorxiv-doi-1'
DUMMY_NON_BIORXIV_MEDRXIV_DOI_1 = '10.1234/dummy-biorxiv-doi-1'

OPENSEARCH_SEARCH_RESULT_1: OpenSearchSearchResultDict = {
    'hits': {
        'hits': [{
            '_source': {
                'doi': DOI_1
            }
        }]
    }
}


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


class TestGetCategorisationResponseDictForOpenSearchAggregationsResponseDict:
    def test_should_return_categories_from_categorisation_response(self):
        categorisaton_response_dict = (
            get_categorisation_response_dict_for_opensearch_aggregations_response_dict({
                'aggregations': {
                    'group_title': {
                        'buckets': [{
                            'key': 'Category 1',
                            'doc_count': 20
                        }, {
                            'key': 'Category 2',
                            'doc_count': 10
                        }]
                    }
                }
            })
        )
        assert categorisaton_response_dict == {
            'data': [{
                'display_name': 'Category 1',
                'type': 'category',
                'source_id': 'crossref_group_title'
            }, {
                'display_name': 'Category 2',
                'type': 'category',
                'source_id': 'crossref_group_title'
            }]
        }


class TestGetCategorisationDictForOpensearchDocumentDict:
    def test_should_return_empty_dict_if_no_categories_are_available(self):
        categories_dict = get_categorisation_response_dict_for_opensearch_document_dict(
            {},
            article_doi=DUMMY_BIORXIV_DOI_1
        )
        assert categories_dict == {
            'data': []
        }

    def test_should_extract_crossref_group_title_as_categories_for_biorxiv_doi(self):
        categories_response_dict = get_categorisation_response_dict_for_opensearch_document_dict(
            {
                'crossref': {
                    'group_title': 'Category 1'
                }
            },
            article_doi=DUMMY_BIORXIV_DOI_1
        )
        assert categories_response_dict == {
            'data': [{
                'display_name': 'Category 1',
                'type': 'category',
                'source_id': 'crossref_group_title'
            }]
        }

    def test_should_ignore_group_title_of_non_biorxiv_medrxiv_doi(self):
        categories_response_dict = get_categorisation_response_dict_for_opensearch_document_dict(
            {
                'crossref': {
                    'group_title': 'Category 1'
                }
            },
            article_doi=DUMMY_NON_BIORXIV_MEDRXIV_DOI_1
        )
        assert categories_response_dict == {
            'data': []
        }


class TestGetArticleResponseDictForOpensearchDocumentDict:
    def test_should_raise_error_if_doi_is_missing(self):
        with pytest.raises(AssertionError):
            get_article_response_dict_for_opensearch_document_dict({})

    def test_should_return_response_with_doi_only(self):
        article_dict = get_article_response_dict_for_opensearch_document_dict({
            'doi': DOI_1
        })
        assert article_dict == {
            'data': {
                'doi': DOI_1
            }
        }


class TestGetArticleSearchResponseDictForOpensearchSearchResponseDict:
    def test_should_return_singe_article_response_from_hits(self):
        article_search_response_dict = (
            get_article_search_response_dict_for_opensearch_search_response_dict({
                'hits': {
                    'hits': [{
                        '_source': {
                            'doi': DOI_1
                        }
                    }]
                }
            })
        )
        assert article_search_response_dict == {
            'data': [{
                'doi': DOI_1
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

    @pytest.mark.asyncio
    async def test_should_return_article_response(
        self,
        async_opensearch_categories_provider: AsyncOpenSearchCategoriesProvider,
        async_opensearch_client_mock: AsyncMock
    ):
        async_opensearch_client_mock.search.return_value = OPENSEARCH_SEARCH_RESULT_1
        article_response = (
            await async_opensearch_categories_provider.get_article_search_response_dict_by_category(
                category='Category 1'
            )
        )
        assert article_response == (
            get_article_search_response_dict_for_opensearch_search_response_dict(
                OPENSEARCH_SEARCH_RESULT_1
            )
        )
