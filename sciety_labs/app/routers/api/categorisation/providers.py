import logging
from typing import List, Mapping, Optional

import opensearchpy

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.api.categorisation.typing import (
    ArticleDict,
    ArticleResponseDict,
    ArticleSearchResponseDict,
    CategorisationDict,
    CategorisationResponseDict
)
from sciety_labs.models.article import KnownDoiPrefix
from sciety_labs.providers.opensearch.typing import (
    DocumentDict,
    OpenSearchSearchResultDict
)
from sciety_labs.providers.opensearch.utils import (
    IS_EVALUATED_OPENSEARCH_FILTER_DICT,
    OpenSearchFilterParameters,
    OpenSearchPaginationParameters,
    OpenSearchSortField,
    OpenSearchSortParameters,
    get_article_meta_from_document,
    get_article_stats_from_document
)
from sciety_labs.utils.datetime import get_date_as_isoformat
from sciety_labs.utils.json import get_recursively_filtered_dict_without_null_values


LOGGER = logging.getLogger(__name__)


IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT = {
    'prefix': {
        'doi': KnownDoiPrefix.BIORXIV_MEDRXIV
    }
}


class ArticleDoiNotFoundError(RuntimeError):
    def __init__(self, article_doi: str):
        self.article_doi = article_doi
        super().__init__(f'Article DOI not found: {article_doi}')


def get_categorisation_list_opensearch_query_dict(
    filter_parameters: OpenSearchFilterParameters
) -> dict:
    filter_dicts: List[dict] = [
        IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT
    ]
    if filter_parameters.evaluated_only:
        filter_dicts.append(IS_EVALUATED_OPENSEARCH_FILTER_DICT)
    return {
        'query': {
            'bool': {
                'filter': filter_dicts
            }
        },
        'aggs': {
            'group_title': {
                'terms': {
                    'field': 'crossref.group_title.keyword',
                    'size': 10000
                }
            }
        },
        'size': 0
    }


def get_category_as_crossref_group_title_opensearch_filter_dict(
    category: str
) -> dict:
    return {
        'term': {
            'crossref.group_title.keyword': category
        }
    }


def get_article_search_by_category_opensearch_query_dict(
    category: str,
    filter_parameters: OpenSearchFilterParameters,
    sort_parameters: OpenSearchSortParameters,
    pagination_parameters: OpenSearchPaginationParameters
) -> dict:
    filter_dicts: List[dict] = [
        IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT,
        get_category_as_crossref_group_title_opensearch_filter_dict(category)
    ]
    if filter_parameters.evaluated_only:
        filter_dicts.append(IS_EVALUATED_OPENSEARCH_FILTER_DICT)
    query_dict: dict = {
        'query': {
            'bool': {
                'filter': filter_dicts
            }
        },
        'size': pagination_parameters.page_size,
        'from': pagination_parameters.get_offset()
    }
    if sort_parameters:
        query_dict['sort'] = sort_parameters.to_opensearch_sort_dict_list()
    return query_dict


def get_categorisation_dict_for_crossref_group_title(
    group_title: str
) -> CategorisationDict:
    return {
        'display_name': group_title,
        'type': 'category',
        'source_id': 'crossref_group_title'
    }


def get_categorisation_response_dict_for_opensearch_aggregations_response_dict(
    response_dict: dict
) -> CategorisationResponseDict:
    group_titles = [
        bucket['key']
        for bucket in response_dict['aggregations']['group_title']['buckets']
    ]
    return {
        'data': [
            get_categorisation_dict_for_crossref_group_title(group_title)
            for group_title in group_titles
        ]
    }


def get_categorisation_response_dict_for_opensearch_document_dict(
    document_dict: dict,
    article_doi: str
) -> CategorisationResponseDict:
    crossref_opensearch_dict = document_dict.get('crossref')
    group_title = (
        crossref_opensearch_dict
        and crossref_opensearch_dict.get('group_title')
    )
    if not group_title or not article_doi.startswith(f'{KnownDoiPrefix.BIORXIV_MEDRXIV}/'):
        return {
            'data': []
        }
    return {
        'data': [
            get_categorisation_dict_for_crossref_group_title(group_title)
        ]
    }


def get_article_dict_for_opensearch_document_dict(
    document_dict: DocumentDict
) -> ArticleDict:
    assert document_dict.get('doi')
    article_meta = get_article_meta_from_document(document_dict)
    article_stats = get_article_stats_from_document(document_dict)
    sciety_dict = document_dict.get('sciety')
    article_dict: ArticleDict = {
        'doi': document_dict['doi'],
        'title': article_meta.article_title,
        'publication_date': get_date_as_isoformat(article_meta.published_date),
        'evaluation_count': (
            article_stats.evaluation_count
            if article_stats
            else None
        ),
        'latest_evaluation_activity_timestamp': (
            sciety_dict.get('last_event_timestamp')
            if sciety_dict
            else None
        )
    }
    return get_recursively_filtered_dict_without_null_values(article_dict)


def get_article_response_dict_for_opensearch_document_dict(
    document_dict: DocumentDict
) -> ArticleResponseDict:
    return {
        'data': get_article_dict_for_opensearch_document_dict(document_dict)
    }


def get_article_search_response_dict_for_opensearch_search_response_dict(
    opensearch_search_result_dict: OpenSearchSearchResultDict
) -> ArticleSearchResponseDict:
    return {
        'meta': {
            'total': opensearch_search_result_dict['hits']['total']['value']
        },
        'data': [
            get_article_dict_for_opensearch_document_dict(
                document_dict=hit['_source']
            )
            for hit in opensearch_search_result_dict['hits']['hits']
        ]
    }


LATEST_EVALUATION_TIMESTAMP_DESC_OPENSEARCH_SORT_FIELD = OpenSearchSortField(
    field_name='sciety.last_event_timestamp',
    sort_order='desc'
)


def get_default_article_search_sort_parameters(
    evaluated_only: bool
) -> OpenSearchSortParameters:
    if evaluated_only:
        return OpenSearchSortParameters(
            sort_fields=[LATEST_EVALUATION_TIMESTAMP_DESC_OPENSEARCH_SORT_FIELD]
        )
    return OpenSearchSortParameters(sort_fields=[])


class AsyncOpenSearchCategoriesProvider:
    def __init__(self, app_providers_and_models: AppProvidersAndModels):
        self.async_opensearch_client = app_providers_and_models.async_opensearch_client
        self.index_name = app_providers_and_models.opensearch_config.index_name

    async def get_categorisation_list_response_dict(
        self,
        filter_parameters: OpenSearchFilterParameters,
        headers: Optional[Mapping[str, str]] = None
    ) -> CategorisationResponseDict:
        LOGGER.info('filter_parameters: %r', filter_parameters)
        LOGGER.debug('async_opensearch_client: %r', self.async_opensearch_client)
        opensearch_aggregations_response_dict = await self.async_opensearch_client.search(
            get_categorisation_list_opensearch_query_dict(
                filter_parameters=filter_parameters
            ),
            index=self.index_name,
            headers=headers
        )
        return get_categorisation_response_dict_for_opensearch_aggregations_response_dict(
            opensearch_aggregations_response_dict
        )

    async def get_categorisation_response_dict_by_doi(
        self,
        article_doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> CategorisationResponseDict:
        LOGGER.debug('async_opensearch_client: %r', self.async_opensearch_client)
        LOGGER.debug(
            'async_opensearch_client.get_source: %r',
            self.async_opensearch_client.get_source
        )
        try:
            opensearch_document_dict = await self.async_opensearch_client.get_source(
                index=self.index_name,
                id=article_doi,
                _source_includes=['crossref.group_title'],
                headers=headers
            )
        except opensearchpy.NotFoundError as exc:
            raise ArticleDoiNotFoundError(article_doi=article_doi) from exc
        return get_categorisation_response_dict_for_opensearch_document_dict(
            opensearch_document_dict,
            article_doi=article_doi
        )

    async def get_article_search_response_dict_by_category(  # pylint: disable=too-many-arguments
        self,
        category: str,
        filter_parameters: OpenSearchFilterParameters,
        sort_parameters: OpenSearchSortParameters,
        pagination_parameters: OpenSearchPaginationParameters,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleSearchResponseDict:
        LOGGER.info('filter_parameters: %r', filter_parameters)
        LOGGER.info('pagination_parameters: %r', pagination_parameters)
        opensearch_search_result_dict = await self.async_opensearch_client.search(
            get_article_search_by_category_opensearch_query_dict(
                category=category,
                filter_parameters=filter_parameters,
                sort_parameters=sort_parameters,
                pagination_parameters=pagination_parameters
            ),
            index=self.index_name,
            headers=headers
        )
        return get_article_search_response_dict_for_opensearch_search_response_dict(
            opensearch_search_result_dict
        )
