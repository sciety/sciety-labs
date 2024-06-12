import logging
from typing import List, Mapping, Optional, Sequence, Set, cast

import opensearchpy

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.api.papers.typing import (
    ArticleAttributesDict,
    ArticleDict,
    ArticleResponseDict,
    ArticleSearchResponseDict,
    CategorisationDict,
    CategorisationResponseDict
)
from sciety_labs.models.article import InternalArticleFieldNames, KnownDoiPrefix
from sciety_labs.providers.opensearch.typing import (
    DocumentDict,
    OpenSearchSearchResultDict
)
from sciety_labs.providers.opensearch.utils import (
    OPENSEARCH_FIELDS_BY_REQUESTED_FIELD,
    OpenSearchFilterParameters,
    OpenSearchPaginationParameters,
    OpenSearchSortField,
    OpenSearchSortParameters,
    get_article_meta_from_document,
    get_article_stats_from_document,
    get_opensearch_filter_dicts_for_filter_parameters,
    get_source_includes_for_mapping
)
from sciety_labs.providers.opensearch.utils import (
    IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT
)
from sciety_labs.utils.datetime import get_date_as_isoformat
from sciety_labs.utils.json import get_recursively_filtered_dict_without_null_values
from sciety_labs.utils.mapping import get_flat_mapped_values_or_all_values_for_mapping


LOGGER = logging.getLogger(__name__)


INTERNAL_ARTICLE_FIELDS_BY_API_FIELD_NAME: Mapping[str, Sequence[str]] = {
    'doi': [InternalArticleFieldNames.ARTICLE_DOI],
    'title': [InternalArticleFieldNames.ARTICLE_TITLE],
    'publication_date': [InternalArticleFieldNames.PUBLISHED_DATE],
    'evaluation_count': [InternalArticleFieldNames.EVALUATION_COUNT],
    'has_evaluations': [InternalArticleFieldNames.EVALUATION_COUNT],
    'latest_evaluation_activity_timestamp': [
        InternalArticleFieldNames.LATEST_EVALUATION_ACTIVITY_TIMESTAMP
    ]
}


class ArticleDoiNotFoundError(RuntimeError):
    def __init__(self, article_doi: str):
        self.article_doi = article_doi
        super().__init__(f'Article DOI not found: {article_doi}')


def get_classification_list_opensearch_query_dict(
    filter_parameters: OpenSearchFilterParameters
) -> dict:
    filter_dicts: List[dict] = [
        IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT
    ]
    filter_dicts.extend(get_opensearch_filter_dicts_for_filter_parameters(
        filter_parameters=filter_parameters
    ))
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


def get_article_search_by_category_opensearch_query_dict(
    filter_parameters: OpenSearchFilterParameters,
    sort_parameters: OpenSearchSortParameters,
    pagination_parameters: OpenSearchPaginationParameters
) -> dict:
    filter_dicts: List[dict] = []
    filter_dicts.extend(get_opensearch_filter_dicts_for_filter_parameters(
        filter_parameters=filter_parameters
    ))
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


def get_classification_dict_for_crossref_group_title(
    group_title: str
) -> CategorisationDict:
    return {
        'type': 'category',
        'id': group_title,
        'attributes': {
            'display_name': group_title,
            'source_id': 'crossref_group_title'
        }
    }


def get_classification_response_dict_for_opensearch_aggregations_response_dict(
    response_dict: dict
) -> CategorisationResponseDict:
    group_titles = [
        bucket['key']
        for bucket in response_dict['aggregations']['group_title']['buckets']
    ]
    return {
        'data': [
            get_classification_dict_for_crossref_group_title(group_title)
            for group_title in group_titles
        ]
    }


def get_classification_response_dict_for_opensearch_document_dict(
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
            get_classification_dict_for_crossref_group_title(group_title)
        ]
    }


def get_article_dict_for_opensearch_document_dict(
    document_dict: DocumentDict,
    article_fields_set: Optional[Set[str]] = None
) -> ArticleDict:
    assert document_dict.get('doi')
    article_meta = get_article_meta_from_document(document_dict)
    article_stats = get_article_stats_from_document(document_dict)
    sciety_dict = document_dict.get('sciety')
    evaluation_count = (
        article_stats.evaluation_count
        if article_stats
        else None
    )
    attributes: ArticleAttributesDict = {
        'doi': document_dict['doi'],
        'title': article_meta.article_title,
        'publication_date': get_date_as_isoformat(article_meta.published_date),
        'evaluation_count': evaluation_count,
        'has_evaluations': (
            bool(evaluation_count)
            if evaluation_count is not None
            else None
        ),
        'latest_evaluation_activity_timestamp': (
            sciety_dict.get('last_event_timestamp')
            if sciety_dict
            else None
        )
    }
    if article_fields_set:
        attributes = cast(ArticleAttributesDict, {
            key: value
            for key, value in attributes.items()
            if key in article_fields_set
        })
    article_dict: ArticleDict = {
        'type': 'article',
        'id': document_dict['doi'],
        'attributes': attributes
    }
    return get_recursively_filtered_dict_without_null_values(article_dict)


def get_article_response_dict_for_opensearch_document_dict(
    document_dict: DocumentDict
) -> ArticleResponseDict:
    return {
        'data': get_article_dict_for_opensearch_document_dict(document_dict)
    }


def get_article_search_response_dict_for_opensearch_search_response_dict(
    opensearch_search_result_dict: OpenSearchSearchResultDict,
    article_fields_set: Optional[Set[str]] = None
) -> ArticleSearchResponseDict:
    return {
        'meta': {
            'total': opensearch_search_result_dict['hits']['total']['value']
        },
        'data': [
            get_article_dict_for_opensearch_document_dict(
                document_dict=hit['_source'],
                article_fields_set=article_fields_set
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


class AsyncOpenSearchClassificationProvider:
    def __init__(self, app_providers_and_models: AppProvidersAndModels):
        self.async_opensearch_client = app_providers_and_models.async_opensearch_client
        self.index_name = app_providers_and_models.opensearch_config.index_name

    async def get_classification_list_response_dict(
        self,
        filter_parameters: OpenSearchFilterParameters,
        headers: Optional[Mapping[str, str]] = None
    ) -> CategorisationResponseDict:
        LOGGER.info('filter_parameters: %r', filter_parameters)
        LOGGER.debug('async_opensearch_client: %r', self.async_opensearch_client)
        opensearch_aggregations_response_dict = await self.async_opensearch_client.search(
            get_classification_list_opensearch_query_dict(
                filter_parameters=filter_parameters
            ),
            index=self.index_name,
            headers=headers
        )
        return get_classification_response_dict_for_opensearch_aggregations_response_dict(
            opensearch_aggregations_response_dict
        )

    async def get_classificiation_response_dict_by_doi(
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
        return get_classification_response_dict_for_opensearch_document_dict(
            opensearch_document_dict,
            article_doi=article_doi
        )

    async def get_article_search_response_dict(  # pylint: disable=too-many-arguments
        self,
        filter_parameters: OpenSearchFilterParameters,
        sort_parameters: OpenSearchSortParameters,
        pagination_parameters: OpenSearchPaginationParameters,
        article_fields_set: Optional[Set[str]] = None,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleSearchResponseDict:
        LOGGER.info('filter_parameters: %r', filter_parameters)
        LOGGER.info('pagination_parameters: %r', pagination_parameters)
        LOGGER.info('article_fields_set: %r', article_fields_set)
        internal_article_fields_set = set(get_flat_mapped_values_or_all_values_for_mapping(
            INTERNAL_ARTICLE_FIELDS_BY_API_FIELD_NAME,
            article_fields_set
        ))
        opensearch_fields = get_source_includes_for_mapping(
            OPENSEARCH_FIELDS_BY_REQUESTED_FIELD,
            fields=internal_article_fields_set
        )
        LOGGER.info('opensearch_fields: %r', opensearch_fields)
        opensearch_search_result_dict = await self.async_opensearch_client.search(
            get_article_search_by_category_opensearch_query_dict(
                filter_parameters=filter_parameters,
                sort_parameters=sort_parameters,
                pagination_parameters=pagination_parameters
            ),
            _source_includes=opensearch_fields,
            index=self.index_name,
            headers=headers
        )
        return get_article_search_response_dict_for_opensearch_search_response_dict(
            opensearch_search_result_dict,
            article_fields_set=article_fields_set
        )
