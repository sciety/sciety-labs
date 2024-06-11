from unittest.mock import AsyncMock, MagicMock

import opensearchpy
import pytest

from sciety_labs.app.routers.api.classification.providers import (
    IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT,
    LATEST_EVALUATION_TIMESTAMP_DESC_OPENSEARCH_SORT_FIELD,
    ArticleDoiNotFoundError,
    AsyncOpenSearchClassificationProvider,
    get_article_dict_for_opensearch_document_dict,
    get_article_response_dict_for_opensearch_document_dict,
    get_article_search_by_category_opensearch_query_dict,
    get_article_search_response_dict_for_opensearch_search_response_dict,
    get_classification_list_opensearch_query_dict,
    get_classification_response_dict_for_opensearch_aggregations_response_dict,
    get_classification_response_dict_for_opensearch_document_dict,
    get_category_as_crossref_group_title_opensearch_filter_dict,
    get_default_article_search_sort_parameters
)
from sciety_labs.providers.opensearch.typing import OpenSearchSearchResultDict
from sciety_labs.providers.opensearch.utils import (
    IS_EVALUATED_OPENSEARCH_FILTER_DICT,
    OpenSearchFilterParameters,
    OpenSearchPaginationParameters,
    OpenSearchSortField,
    OpenSearchSortParameters
)


DOI_1 = '10.12345/test-doi-1'

DUMMY_BIORXIV_DOI_1 = '10.1101/dummy-biorxiv-doi-1'
DUMMY_NON_BIORXIV_MEDRXIV_DOI_1 = '10.1234/dummy-biorxiv-doi-1'

OPENSEARCH_SEARCH_RESULT_DOCUMENT_1: dict = {
    'doi': DOI_1
}

OPENSEARCH_SEARCH_RESULT_1: OpenSearchSearchResultDict = {
    'hits': {
        'total': {
            'value': 1,
            'relation': 'eq'
        },
        'hits': [{'_source': OPENSEARCH_SEARCH_RESULT_DOCUMENT_1}]
    }
}


@pytest.fixture(name='async_opensearch_classification_provider')
def _async_opensearch_classification_provider(
    app_providers_and_models_mock: MagicMock
) -> AsyncOpenSearchClassificationProvider:
    return AsyncOpenSearchClassificationProvider(
        app_providers_and_models=app_providers_and_models_mock
    )


class TestArticleDoiNotFoundError:
    def test_should_include_doi_in_str_and_repr(self):
        exception = ArticleDoiNotFoundError(article_doi=DOI_1)
        assert DOI_1 in str(exception)
        assert DOI_1 in repr(exception)


class TestGetClassificationListOpenSearchQueryDict:
    def test_should_include_biorxiv_medrxiv_filter(self):
        query_dict = get_classification_list_opensearch_query_dict(
            filter_parameters=OpenSearchFilterParameters(has_evaluations=False)
        )
        assert query_dict['query']['bool']['filter'] == [
            IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT
        ]

    def test_should_include_has_evaluations_filter(self):
        query_dict = get_classification_list_opensearch_query_dict(
            filter_parameters=OpenSearchFilterParameters(has_evaluations=True)
        )
        assert query_dict['query']['bool']['filter'] == [
            IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT,
            IS_EVALUATED_OPENSEARCH_FILTER_DICT
        ]


class TestGetArticleSearchByCategoryOpenSearchQueryDict:
    def test_should_include_category_filter(self):
        query_dict = get_article_search_by_category_opensearch_query_dict(
            category='Category 1',
            filter_parameters=OpenSearchFilterParameters(has_evaluations=None),
            sort_parameters=OpenSearchSortParameters(),
            pagination_parameters=OpenSearchPaginationParameters()
        )
        assert query_dict['query'] == {
            'bool': {
                'filter': [
                    IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT,
                    get_category_as_crossref_group_title_opensearch_filter_dict('Category 1')
                ]
            }
        }

    def test_should_include_category_and_has_evaluations_filter(self):
        query_dict = get_article_search_by_category_opensearch_query_dict(
            category='Category 1',
            filter_parameters=OpenSearchFilterParameters(has_evaluations=True),
            sort_parameters=OpenSearchSortParameters(),
            pagination_parameters=OpenSearchPaginationParameters()
        )
        assert query_dict['query']['bool']['filter'] == [
            IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT,
            get_category_as_crossref_group_title_opensearch_filter_dict('Category 1'),
            IS_EVALUATED_OPENSEARCH_FILTER_DICT
        ]

    def test_should_include_category_and_negative_has_evaluations_filter(self):
        query_dict = get_article_search_by_category_opensearch_query_dict(
            category='Category 1',
            filter_parameters=OpenSearchFilterParameters(has_evaluations=False),
            sort_parameters=OpenSearchSortParameters(),
            pagination_parameters=OpenSearchPaginationParameters()
        )
        assert query_dict['query']['bool']['filter'] == [
            IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT,
            get_category_as_crossref_group_title_opensearch_filter_dict('Category 1'),
            {'bool': {'must_not': [IS_EVALUATED_OPENSEARCH_FILTER_DICT]}}
        ]

    def test_should_be_able_to_sort_by_latest_evaluation_activity(self):
        query_dict = get_article_search_by_category_opensearch_query_dict(
            category='Category 1',
            filter_parameters=OpenSearchFilterParameters(has_evaluations=True),
            sort_parameters=OpenSearchSortParameters(sort_fields=[OpenSearchSortField(
                field_name='sciety.last_event_timestamp',
                sort_order='desc'
            )]),
            pagination_parameters=OpenSearchPaginationParameters()
        )
        assert query_dict['sort'] == [
            {
                'sciety.last_event_timestamp': {
                    'order': 'desc'
                }
            }
        ]

    def test_should_use_page_size_and_page_number(self):
        query_dict = get_article_search_by_category_opensearch_query_dict(
            category='Category 1',
            filter_parameters=OpenSearchFilterParameters(has_evaluations=True),
            sort_parameters=OpenSearchSortParameters(sort_fields=[]),
            pagination_parameters=OpenSearchPaginationParameters(
                page_size=100,
                page_number=3
            )
        )
        assert query_dict['size'] == 100
        assert query_dict['from'] == 200


class TestGetClassificationResponseDictForOpenSearchAggregationsResponseDict:
    def test_should_return_classifications_from_classification_response(self):
        classification_response_dict = (
            get_classification_response_dict_for_opensearch_aggregations_response_dict({
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
        assert classification_response_dict == {
            'data': [{
                'type': 'category',
                'id': 'Category 1',
                'attributes': {
                    'display_name': 'Category 1',
                    'source_id': 'crossref_group_title'
                }
            }, {
                'type': 'category',
                'id': 'Category 2',
                'attributes': {
                    'display_name': 'Category 2',
                    'source_id': 'crossref_group_title'
                }
            }]
        }


class TestGetClassificationDictForOpenSearchDocumentDict:
    def test_should_return_empty_dict_if_no_classifications_are_available(self):
        classifications_dict = get_classification_response_dict_for_opensearch_document_dict(
            {},
            article_doi=DUMMY_BIORXIV_DOI_1
        )
        assert classifications_dict == {
            'data': []
        }

    def test_should_extract_crossref_group_title_as_classifications_for_biorxiv_doi(self):
        classifications_response_dict = (
            get_classification_response_dict_for_opensearch_document_dict(
                {
                    'crossref': {
                        'group_title': 'Category 1'
                    }
                },
                article_doi=DUMMY_BIORXIV_DOI_1
            )
        )
        assert classifications_response_dict == {
            'data': [{
                'type': 'category',
                'id': 'Category 1',
                'attributes': {
                    'display_name': 'Category 1',
                    'source_id': 'crossref_group_title'
                }
            }]
        }

    def test_should_ignore_group_title_of_non_biorxiv_medrxiv_doi(self):
        classifications_response_dict = (
            get_classification_response_dict_for_opensearch_document_dict(
                {
                    'crossref': {
                        'group_title': 'Category 1'
                    }
                },
                article_doi=DUMMY_NON_BIORXIV_MEDRXIV_DOI_1
            )
        )
        assert classifications_response_dict == {
            'data': []
        }


class TestGetArticleDictForOpenSearchDocumentDict:
    def test_should_raise_error_if_doi_is_missing(self):
        with pytest.raises(AssertionError):
            get_article_dict_for_opensearch_document_dict({})

    def test_should_return_response_with_doi_only(self):
        article_dict = get_article_dict_for_opensearch_document_dict({
            'doi': DOI_1
        })
        assert article_dict == {
            'type': 'article',
            'id': DOI_1,
            'attributes': {
                'doi': DOI_1
            }
        }

    def test_should_return_response_with_crossref_metadata(self):
        article_dict = get_article_dict_for_opensearch_document_dict({
            'doi': DOI_1,
            'id': DOI_1,
            'crossref': {
                'title_with_markup': 'Title 1',
                'publication_date': '2001-02-03'
            }
        })
        assert article_dict == {
            'type': 'article',
            'id': DOI_1,
            'attributes': {
                'doi': DOI_1,
                'title': 'Title 1',
                'publication_date': '2001-02-03'
            }
        }

    def test_should_return_response_with_evaluation_count_and_timestamp(self):
        article_dict = get_article_dict_for_opensearch_document_dict({
            'doi': DOI_1,
            'sciety': {
                'evaluation_count': 123,
                'last_event_timestamp': '2001-02-03T04:05:06+00:00'
            }
        })
        assert article_dict == {
            'type': 'article',
            'id': DOI_1,
            'attributes': {
                'doi': DOI_1,
                'evaluation_count': 123,
                'has_evaluations': True,
                'latest_evaluation_activity_timestamp': '2001-02-03T04:05:06+00:00'
            }
        }

    def test_should_filter_attributes(self):
        article_dict = get_article_dict_for_opensearch_document_dict(
            {
                'doi': DOI_1,
                'sciety': {
                    'evaluation_count': 123,
                    'last_event_timestamp': '2001-02-03T04:05:06+00:00'
                }
            },
            article_fields_set={'doi', 'has_evaluations'}
        )
        assert article_dict == {
            'type': 'article',
            'id': DOI_1,
            'attributes': {
                'doi': DOI_1,
                'has_evaluations': True
            }
        }


class TestGetArticleResponseDictForOpenSearchDocumentDict:
    def test_should_return_response_as_data_object(self):
        article_dict = get_article_response_dict_for_opensearch_document_dict(
            OPENSEARCH_SEARCH_RESULT_DOCUMENT_1
        )
        assert article_dict == {
            'data': get_article_dict_for_opensearch_document_dict(
                OPENSEARCH_SEARCH_RESULT_DOCUMENT_1
            )
        }


class TestGetArticleSearchResponseDictForOpenSearchSearchResponseDict:
    def test_should_return_singe_article_response_from_hits(self):
        article_search_response_dict = (
            get_article_search_response_dict_for_opensearch_search_response_dict({
                'hits': {
                    'total': {
                        'value': 1,
                        'relation': 'eq'
                    },
                    'hits': [{
                        '_source': OPENSEARCH_SEARCH_RESULT_DOCUMENT_1
                    }]
                }
            })
        )
        assert article_search_response_dict == {
            'data': [
                get_article_dict_for_opensearch_document_dict(
                    OPENSEARCH_SEARCH_RESULT_DOCUMENT_1
                )
            ],
            'meta': {
                'total': 1
            }
        }


class TestGetDefaultArticleSearchSortParameters:
    def test_should_not_sort_by_if_not_evaluation_only(self):
        sort_parameters = get_default_article_search_sort_parameters(
            has_evaluations=False
        )
        assert not sort_parameters.sort_fields
        assert not sort_parameters

    def test_should_sort_by_evaluation_activity_descending_if_evaluation_only(self):
        sort_parameters = get_default_article_search_sort_parameters(
            has_evaluations=True
        )
        assert sort_parameters == OpenSearchSortParameters(sort_fields=[
            LATEST_EVALUATION_TIMESTAMP_DESC_OPENSEARCH_SORT_FIELD
        ])


class TestAsyncOpenSearchClassificationProvider:
    @pytest.mark.asyncio
    async def test_should_raise_article_doi_not_found_error(
        self,
        async_opensearch_classification_provider: AsyncOpenSearchClassificationProvider,
        async_opensearch_client_mock: AsyncMock
    ):
        async_opensearch_client_mock.get_source.side_effect = opensearchpy.NotFoundError()
        with pytest.raises(ArticleDoiNotFoundError):
            await async_opensearch_classification_provider.get_classificiation_response_dict_by_doi(
                article_doi=DOI_1
            )

    @pytest.mark.asyncio
    async def test_should_return_article_response(
        self,
        async_opensearch_classification_provider: AsyncOpenSearchClassificationProvider,
        async_opensearch_client_mock: AsyncMock
    ):
        async_opensearch_client_mock.search.return_value = OPENSEARCH_SEARCH_RESULT_1
        article_response = await (
            async_opensearch_classification_provider
            .get_article_search_response_dict_by_category(
                category='Category 1',
                filter_parameters=OpenSearchFilterParameters(),
                sort_parameters=OpenSearchSortParameters(),
                pagination_parameters=OpenSearchPaginationParameters()
            )
        )
        assert article_response == (
            get_article_search_response_dict_for_opensearch_search_response_dict(
                OPENSEARCH_SEARCH_RESULT_1
            )
        )
