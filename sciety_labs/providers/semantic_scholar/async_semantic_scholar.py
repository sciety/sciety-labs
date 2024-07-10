from datetime import date
import logging
import os
from pathlib import Path
from typing import AsyncIterator, Mapping, Optional, Sequence

import aiohttp

from sciety_labs.models.article import ArticleMention, ArticleSearchResultItem
from sciety_labs.models.evaluation import ScietyEventEvaluationStatsModel
from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider
from sciety_labs.providers.search import (
    AsyncSearchProvider,
    SearchDateRange,
    SearchParameters,
    SearchSortBy
)
from sciety_labs.providers.semantic_scholar.semantic_scholar import (
    get_semantic_scholar_api_key_file_path,
    get_year_request_parameter_for_date_range,
    iter_article_search_result_item_from_search_response_json
)
from sciety_labs.providers.semantic_scholar.utils import (
    DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT,
    MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET,
    MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT,
    SEMANTIC_SCHOLAR_REQUESTED_FIELDS,
    SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITH_VENUES,
    ArticleSearchResultList
)
from sciety_labs.utils.async_utils import async_iter_sync_iterable, get_list_for_async_iterable


LOGGER = logging.getLogger(__name__)


async def async_is_data_for_limit_or_offset_not_available_error(
    response: aiohttp.ClientResponse
) -> bool:
    try:
        return (
            response.status == 400
            and (
                (await response.json()).get('error')
                == 'Requested data for this limit and/or offset is not available'
            )
        )
    except aiohttp.client_exceptions.ContentTypeError:
        return False


async def async_iter_search_results_published_within_date_range(
    search_result_iterable: AsyncIterator[ArticleSearchResultItem],
    from_date: date,
    to_date: date
) -> AsyncIterator[ArticleSearchResultItem]:
    async for search_result in search_result_iterable:
        if not search_result.article_meta:
            continue
        published_date = search_result.article_meta.published_date
        if not published_date:
            continue
        if from_date <= published_date <= to_date:
            yield search_result


class AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider(AsyncRequestsProvider):
    async def get_embedding_vector(
        self,
        title: str,
        abstract: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> Sequence[float]:
        paper_id = '_dummy_paper_id'
        papers = [{
            'paper_id': paper_id,
            'title': title,
            'abstract': abstract
        }]
        async with self.client_session.post(
            'https://model-apis.semanticscholar.org/specter/v1/invoke',
            json=papers,
            timeout=self.timeout,
            headers=self.get_headers(headers=headers)
        ) as response:
            response.raise_for_status()
            response_json = await response.json()
            embeddings_by_paper_id = {
                pred['paper_id']: pred['embedding']
                for pred in response_json.get('preds')
            }
            return embeddings_by_paper_id[paper_id]


class AsyncSemanticScholarProvider(AsyncRequestsProvider):
    def __init__(
        self,
        api_key_file_path: Optional[str],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        if api_key_file_path:
            api_key = Path(api_key_file_path).read_text(encoding='utf-8')
            self.headers['x-api-key'] = api_key

    async def get_search_result_list(
        self,
        query: str,
        additional_search_parameters: Optional[Mapping[str, str]] = None,
        offset: int = 0,
        limit: int = DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT
    ) -> ArticleSearchResultList:
        request_params = {
            **(additional_search_parameters or {}),
            'query': query,
            'fields': ','.join(SEMANTIC_SCHOLAR_REQUESTED_FIELDS),
            'offset': str(offset),
            'limit': str(limit)
        }
        LOGGER.info('Semantic Scholar search, request_params=%r', request_params)
        async with self.get(
            'https://api.semanticscholar.org/graph/v1/paper/search',
            params=request_params,
            timeout=self.timeout,
            headers=self.get_headers()
        ) as response:
            LOGGER.info('Semantic Scholar search, url=%r', response.request_info.url)

            if await async_is_data_for_limit_or_offset_not_available_error(response):
                LOGGER.info('Semantic Scholar search, offset/limit error for offset=%r', offset)
                return ArticleSearchResultList(items=[], offset=offset, total=offset)

            response.raise_for_status()
            response_json = await response.json()
            LOGGER.debug('Semantic Scholar search, response_json=%r', response_json)
        return ArticleSearchResultList(
            items=list(iter_article_search_result_item_from_search_response_json(
                response_json
            )),
            offset=response_json['offset'],
            total=response_json['total'],
            next_offset=response_json.get('next')
        )

    async def iter_unfiltered_search_result_item(
        self,
        query: str,
        additional_search_parameters: Optional[Mapping[str, str]] = None,
        items_per_page: int = DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT
    ) -> AsyncIterator[ArticleSearchResultItem]:
        offset = 0
        while True:
            search_result_list = await self.get_search_result_list(
                query=query,
                additional_search_parameters=additional_search_parameters,
                offset=offset,
                limit=items_per_page
            )
            LOGGER.info('Semantic Scholar search, total=%r', search_result_list.total)
            for item in search_result_list.items:
                yield item
            if not search_result_list.next_offset:
                LOGGER.info('no more search results (no next offset)')
                break
            offset = search_result_list.next_offset
            if offset > MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET:
                LOGGER.info('reached max offset')
                break
            items_per_page = min(
                items_per_page,
                MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT - offset
            )


class AsyncSemanticScholarSearchProvider(AsyncSearchProvider):
    def __init__(
        self,
        async_semantic_scholar_provider: AsyncSemanticScholarProvider,
        evaluation_stats_model: ScietyEventEvaluationStatsModel
    ) -> None:
        self.async_semantic_scholar_provider = async_semantic_scholar_provider
        self.evaluation_stats_model = evaluation_stats_model

    async def iter_search_result_item(
        self,
        search_parameters: SearchParameters
    ) -> AsyncIterator[ArticleSearchResultItem]:
        from_date = SearchDateRange.get_from_date(search_parameters.date_range)
        to_date = SearchDateRange.get_to_date(search_parameters.date_range)
        search_result_iterable: AsyncIterator[ArticleSearchResultItem]
        search_result_iterable = (
            self
            .async_semantic_scholar_provider
            .iter_unfiltered_search_result_item(
                query=search_parameters.query,
                additional_search_parameters={
                    **SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITH_VENUES,
                    'year': get_year_request_parameter_for_date_range(
                        from_date=from_date,
                        to_date=to_date
                    )
                }
            )
        )
        if search_parameters.is_evaluated_only:
            search_result_iterable = (
                self.evaluation_stats_model.async_iter_evaluated_only_article_mention(
                    search_result_iterable
                )
            )
        search_result_iterable = async_iter_search_results_published_within_date_range(
            search_result_iterable,
            from_date=from_date,
            to_date=to_date
        )
        if search_parameters.sort_by == SearchSortBy.PUBLICATION_DATE:
            search_result_iterable = async_iter_sync_iterable(sorted(
                await get_list_for_async_iterable(search_result_iterable),
                key=ArticleMention.get_published_date_sort_key,
                reverse=True
            ))
        async for item in search_result_iterable:
            yield item


def get_async_semantic_scholar_provider(
    **kwargs
) -> Optional[AsyncSemanticScholarProvider]:
    api_key_file_path = get_semantic_scholar_api_key_file_path()
    if api_key_file_path and not os.path.exists(api_key_file_path):
        LOGGER.info(
            'Semantic Scholar API key file does not exist, not using api key: %r',
            api_key_file_path
        )
        api_key_file_path = None
    LOGGER.info('Semantic Scholar API key: %r', api_key_file_path)
    return AsyncSemanticScholarProvider(api_key_file_path, **kwargs)
