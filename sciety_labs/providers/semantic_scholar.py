import dataclasses
import itertools
import logging
from datetime import date, datetime
import os
from pathlib import Path
from typing import AsyncIterator, Iterable, Mapping, Optional, Sequence

import aiohttp
from aiohttp_client_cache.response import CachedResponse

from sciety_labs.models.article import (
    ArticleMention,
    ArticleMetaData,
    ArticleSearchResultItem,
    iter_preprint_article_mention
)
from sciety_labs.models.evaluation import ScietyEventEvaluationStatsModel
from sciety_labs.providers.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationList,
    ArticleRecommendationProvider
)
from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider
from sciety_labs.providers.search import (
    SearchDateRange,
    SearchParameters,
    SearchProvider,
    SearchSortBy
)
from sciety_labs.utils.async_utils import (
    async_iter_sync_iterable,
    get_list_for_async_iterable
)
from sciety_labs.utils.datetime import get_utc_timestamp_with_tzinfo, get_utcnow, parse_date_or_none


LOGGER = logging.getLogger(__name__)


SEMANTIC_SCHOLAR_API_KEY_FILE_PATH_ENV_VAR = 'SEMANTIC_SCHOLAR_API_KEY_FILE_PATH'


MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS = 100

MAX_SEMANTIC_SCHOLAR_SEARCH_ITEMS = 100
MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT = 9999
MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET = MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT - 1


# This is the number of recommendations we ask Semantic Scholar to generate,
# before post filtering
DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS = 500

DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT = 100


SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID = 'semantic_scholar_paper_id'


SEMANTIC_SCHOLAR_REQUESTED_FIELDS = [
    'externalIds',
    'url',
    'title',
    'abstract',
    'authors',
    'publicationDate'
]

SEMANTIC_SCHOLAR_SEARCH_VENUES = ['bioRxiv', 'medRxiv', 'Research Square']

SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITHOUT_VENUES: dict = {'year': 2023}
SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITH_VENUES: dict = {
    **SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITHOUT_VENUES,
    'venue': ','.join(SEMANTIC_SCHOLAR_SEARCH_VENUES)
}


@dataclasses.dataclass(frozen=True)
class ArticleSearchResultList:
    items: Sequence[ArticleSearchResultItem]
    offset: int
    total: int
    next_offset: Optional[int] = None


def _get_recommendation_request_payload_for_paper_ids_or_external_ids(
    paper_ids_or_external_ids: Iterable[str]
) -> dict:
    return {
        'positivePaperIds': list(itertools.islice(
            paper_ids_or_external_ids,
            MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS
        )),
        'negativePaperIds': []
    }


def _get_author_names_from_author_list_json(
    author_list_json: Sequence[dict]
) -> Sequence[str]:
    return [author['name'] for author in author_list_json]


def _get_author_names_from_recommended_paper_json(
    recommended_paper_json: dict
) -> Optional[Sequence[str]]:
    author_list_json = recommended_paper_json.get('authors')
    if not author_list_json:
        return None
    return _get_author_names_from_author_list_json(author_list_json)


def _get_article_meta_from_paper_json(
    paper_json: dict
) -> ArticleMetaData:
    article_doi = paper_json.get('externalIds', {}).get('DOI')
    assert article_doi
    return ArticleMetaData(
        article_doi=article_doi,
        article_title=paper_json['title'],
        published_date=parse_date_or_none(paper_json.get('publicationDate')),
        author_name_list=_get_author_names_from_recommended_paper_json(
            paper_json
        )
    )


def _iter_article_recommendation_from_recommendation_response_json(
    recommendation_response_json: dict
) -> Iterable[ArticleRecommendation]:
    for recommended_paper_json in recommendation_response_json['recommendedPapers']:
        article_doi = recommended_paper_json.get('externalIds', {}).get('DOI')
        if not article_doi:
            continue
        yield ArticleRecommendation(
            article_doi=article_doi,
            article_meta=_get_article_meta_from_paper_json(recommended_paper_json),
            external_reference_by_name={
                SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: recommended_paper_json.get('paperId')
            }
        )


def _iter_article_search_result_item_from_search_response_json(
    search_response_json: dict
) -> Iterable[ArticleSearchResultItem]:
    for item_json in search_response_json.get('data', []):
        article_doi = item_json.get('externalIds', {}).get('DOI')
        if not article_doi:
            continue
        yield ArticleSearchResultItem(
            article_doi=article_doi,
            article_meta=_get_article_meta_from_paper_json(item_json),
            external_reference_by_name={
                SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: item_json.get('paperId')
            }
        )


def get_response_timestamp(response: aiohttp.ClientResponse) -> datetime:
    if isinstance(response, CachedResponse):
        return get_utc_timestamp_with_tzinfo(response.created_at)
    return get_utcnow()


async def is_data_for_limit_or_offset_not_available_error(
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


class SemanticScholarProvider(AsyncRequestsProvider, ArticleRecommendationProvider):
    def __init__(
        self,
        api_key_file_path: Optional[str],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        if api_key_file_path:
            api_key = Path(api_key_file_path).read_text(encoding='utf-8')
            self.headers['x-api-key'] = api_key

    def iter_paper_ids_or_external_ids_for_article_dois(
        self,
        article_dois: Sequence[str]
    ) -> Iterable[str]:
        for doi in article_dois:
            yield f'DOI:{doi}'

    async def get_article_recommendation_list_for_article_dois(
        self,
        article_dois: Iterable[str],
        max_recommendations: Optional[int] = None
    ) -> ArticleRecommendationList:
        if not max_recommendations:
            max_recommendations = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
        request_json = _get_recommendation_request_payload_for_paper_ids_or_external_ids(
            paper_ids_or_external_ids=self.iter_paper_ids_or_external_ids_for_article_dois(
                article_dois=list(itertools.islice(
                    article_dois,
                    MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS
                ))
            )
        )
        LOGGER.info('Semantic Scholar, request_json=%r', request_json)
        async with self.client_session.post(
            'https://api.semanticscholar.org/recommendations/v1/papers/',
            json=request_json,
            params={
                'fields': ','.join(SEMANTIC_SCHOLAR_REQUESTED_FIELDS),
                'limit': str(max_recommendations)
            },
            timeout=self.timeout,
            headers=self.get_headers()
        ) as response:
            response.raise_for_status()
            response_json = await response.json()
            LOGGER.debug('Semantic Scholar, response_json=%r', response_json)
            recommendation_timestamp = get_response_timestamp(response)
        return ArticleRecommendationList(
            recommendations=list(iter_preprint_article_mention(
                _iter_article_recommendation_from_recommendation_response_json(
                    response_json
                )
            )),
            recommendation_timestamp=recommendation_timestamp
        )

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
        async with self.client_session.get(
            'https://api.semanticscholar.org/graph/v1/paper/search',
            params=request_params,
            timeout=self.timeout,
            headers=self.get_headers()
        ) as response:
            LOGGER.info('Semantic Scholar search, url=%r', response.request_info.url)

            if await is_data_for_limit_or_offset_not_available_error(response):
                LOGGER.info('Semantic Scholar search, offset/limit error for offset=%r', offset)
                return ArticleSearchResultList(items=[], offset=offset, total=offset)

            response.raise_for_status()
            response_json = await response.json()
            LOGGER.debug('Semantic Scholar search, response_json=%r', response_json)
        return ArticleSearchResultList(
            items=list(_iter_article_search_result_item_from_search_response_json(
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


def get_year_request_parameter_for_date_range(
    from_date: date,
    to_date: date
) -> str:
    from_year = from_date.year
    to_year = to_date.year
    if to_year == from_year:
        return str(from_year)
    return f'{from_year}-{to_year}'


async def iter_search_results_published_within_date_range(
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


class SemanticScholarSearchProvider(SearchProvider):
    def __init__(
        self,
        semantic_scholar_provider: SemanticScholarProvider,
        evaluation_stats_model: ScietyEventEvaluationStatsModel
    ) -> None:
        self.semantic_scholar_provider = semantic_scholar_provider
        self.evaluation_stats_model = evaluation_stats_model

    async def iter_search_result_item(
        self,
        search_parameters: SearchParameters
    ) -> AsyncIterator[ArticleSearchResultItem]:
        from_date = SearchDateRange.get_from_date(search_parameters.date_range)
        to_date = SearchDateRange.get_to_date(search_parameters.date_range)
        search_result_iterable: AsyncIterator[ArticleSearchResultItem]
        search_result_iterable = self.semantic_scholar_provider.iter_unfiltered_search_result_item(
            query=search_parameters.query,
            additional_search_parameters={
                **SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITH_VENUES,
                'year': get_year_request_parameter_for_date_range(
                    from_date=from_date,
                    to_date=to_date
                )
            }
        )
        if search_parameters.is_evaluated_only:
            search_result_iterable = (
                self.evaluation_stats_model.async_iter_evaluated_only_article_mention(
                    search_result_iterable
                )
            )
        search_result_iterable = iter_search_results_published_within_date_range(
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


def get_semantic_scholar_api_key_file_path() -> Optional[str]:
    return os.getenv(SEMANTIC_SCHOLAR_API_KEY_FILE_PATH_ENV_VAR)


def get_semantic_scholar_provider(
    **kwargs
) -> Optional[SemanticScholarProvider]:
    api_key_file_path = get_semantic_scholar_api_key_file_path()
    if api_key_file_path and not os.path.exists(api_key_file_path):
        LOGGER.info(
            'Semantic Scholar API key file does not exist, not using api key: %r',
            api_key_file_path
        )
        api_key_file_path = None
    LOGGER.info('Semantic Scholar API key: %r', api_key_file_path)
    return SemanticScholarProvider(api_key_file_path, **kwargs)
