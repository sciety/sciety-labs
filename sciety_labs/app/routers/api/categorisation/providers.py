import logging
from typing import Mapping, Optional

import opensearchpy

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.api.categorisation.typing import (
    ArticleDict,
    ArticleResponseDict,
    ArticleSearchResponseDict,
    CategorisationResponseDict
)
from sciety_labs.providers.opensearch_article_recommendation import DocumentDict
from sciety_labs.providers.opensearch.typing import OpenSearchSearchResultDict


LOGGER = logging.getLogger(__name__)


class ArticleDoiNotFoundError(RuntimeError):
    def __init__(self, article_doi: str):
        self.article_doi = article_doi
        super().__init__(f'Article DOI not found: {article_doi}')


def get_categorisation_list_opensearch_query_dict(
) -> dict:
    return {
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
    category: str
) -> dict:
    return {
        'query': {
            'bool': {
                'filter': [
                    {
                        'term': {
                            'crossref.group_title.keyword': category
                        }
                    }
                ]
            }
        }
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
            {
                'display_name': group_title,
                'type': 'category',
                'source_id': 'crossref_group_title'
            }
            for group_title in group_titles
        ]
    }


def get_categorisation_response_dict_for_opensearch_document_dict(
    document_dict: dict
) -> CategorisationResponseDict:
    crossref_opensearch_dict = document_dict.get('crossref')
    group_title = (
        crossref_opensearch_dict
        and crossref_opensearch_dict.get('group_title')
    )
    if not group_title:
        return {
            'data': []
        }
    return {
        'data': [{
            'display_name': group_title,
            'type': 'category',
            'source_id': 'crossref_group_title'
        }]
    }


def get_article_dict_for_opensearch_document_dict(
    document_dict: DocumentDict
) -> ArticleDict:
    assert document_dict.get('doi')
    return {
        'doi': document_dict['doi']
    }


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
        'data': [
            get_article_dict_for_opensearch_document_dict(
                document_dict=hit['_source']
            )
            for hit in opensearch_search_result_dict['hits']['hits']
        ]
    }


class AsyncOpenSearchCategoriesProvider:
    def __init__(self, app_providers_and_models: AppProvidersAndModels):
        self.async_opensearch_client = app_providers_and_models.async_opensearch_client
        self.index_name = app_providers_and_models.opensearch_config.index_name

    async def get_categorisation_list_response_dict(
        self,
        headers: Optional[Mapping[str, str]] = None
    ) -> CategorisationResponseDict:
        LOGGER.debug('async_opensearch_client: %r', self.async_opensearch_client)
        opensearch_aggregations_response_dict = await self.async_opensearch_client.search(
            get_categorisation_list_opensearch_query_dict(),
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
            opensearch_document_dict
        )

    async def get_article_search_response_dict_by_category(
        self,
        category: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleSearchResponseDict:
        opensearch_search_result_dict = await self.async_opensearch_client.search(
            get_article_search_by_category_opensearch_query_dict(
                category=category
            ),
            index=self.index_name,
            headers=headers
        )
        return get_article_search_response_dict_for_opensearch_search_response_dict(
            opensearch_search_result_dict
        )
