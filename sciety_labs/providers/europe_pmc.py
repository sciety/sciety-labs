import dataclasses
from datetime import date
import logging
from typing import AsyncIterator, Iterable, Optional, Sequence

from sciety_labs.models.article import ArticleMetaData, ArticleSearchResultItem
from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider
from sciety_labs.providers.search import (
    SearchDateRange,
    SearchParameters,
    SearchProvider,
    SearchSortBy
)


LOGGER = logging.getLogger(__name__)


DEFAULT_EUROPE_PMC_SEARCH_RESULT_LIMIT = 100

START_CURSOR = '*'

EUROPE_PMC_PREPRINT_SERVERS = ['bioRxiv', 'medRxiv', 'Research Square', 'SciELO Preprints']


@dataclasses.dataclass(frozen=True)
class CursorBasedArticleSearchResultList:
    items: Sequence[ArticleSearchResultItem]
    cursor: str
    total: int
    next_cursor: Optional[str]


def _iter_article_search_result_item_from_search_response_json(
    search_response_json: dict
) -> Iterable[ArticleSearchResultItem]:
    for item_json in search_response_json.get('resultList', {}).get('result', []):
        article_doi = item_json.get('doi')
        if not article_doi:  # pylint: disable=duplicate-code
            continue
        yield ArticleSearchResultItem(
            article_doi=article_doi,
            article_meta=ArticleMetaData(
                article_doi=article_doi,
                article_title=item_json['title']
            )
        )


def get_preprint_servers_query(preprint_servers: Sequence[str]) -> str:
    return ' OR '.join([
        f'PUBLISHER:"{preprint_server}"'
        for preprint_server in preprint_servers
    ])


def get_first_published_date_within_dates(from_date: date, to_date: date) -> str:
    return f'(FIRST_PDATE:[{from_date.isoformat()} TO {to_date.isoformat()}])'


def get_query_with_additional_filters(search_parameters: SearchParameters) -> str:
    preprint_servers_query = get_preprint_servers_query(EUROPE_PMC_PREPRINT_SERVERS)
    result = f'({preprint_servers_query})'
    if search_parameters.is_evaluated_only:
        result += ' (LABS_PUBS:"2112")'
    result += ' ' + get_first_published_date_within_dates(
        SearchDateRange.get_from_date(search_parameters.date_range),
        SearchDateRange.get_to_date(search_parameters.date_range)
    )
    result += f' ({search_parameters.query})'
    if search_parameters.sort_by == SearchSortBy.PUBLICATION_DATE:
        result += ' sort_date:y'
    return result


class EuropePmcProvider(AsyncRequestsProvider, SearchProvider):
    async def get_search_result_list(  # pylint: disable=too-many-arguments
        self,
        search_parameters: SearchParameters,
        cursor: str = START_CURSOR
    ) -> CursorBasedArticleSearchResultList:
        request_params = {
            **(search_parameters.additional_search_parameters or {}),
            'query': get_query_with_additional_filters(
                search_parameters
            ),
            'format': 'json',
            'cursorMark': cursor,
            'pageSize': str(search_parameters.items_per_page)
        }
        LOGGER.info('Europe PMC search, request_params=%r', request_params)
        async with self.client_session.get(
            'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
            params=request_params,
            timeout=self.timeout,
            headers=self.get_headers()
        ) as response:
            LOGGER.info('Europe PMC search, url=%r', response.request_info.url)
            response.raise_for_status()
            response_json = await response.json()
            LOGGER.debug('Europe PMC search, response_json=%r', response_json)
        return CursorBasedArticleSearchResultList(
            items=list(_iter_article_search_result_item_from_search_response_json(
                response_json
            )),
            cursor=response_json['request']['cursorMark'],
            total=response_json['hitCount'],
            next_cursor=response_json.get('nextCursorMark')
        )

    async def iter_search_result_item(
        self,
        search_parameters: SearchParameters
    ) -> AsyncIterator[ArticleSearchResultItem]:
        cursor = START_CURSOR
        while True:
            search_result_list: CursorBasedArticleSearchResultList
            search_result_list = await self.get_search_result_list(
                search_parameters=search_parameters,
                cursor=cursor
            )
            for item in search_result_list.items:
                yield item
            if not search_result_list.next_cursor or search_result_list.next_cursor == cursor:
                LOGGER.info('no more search results (no next cursor)')
                break
            cursor = search_result_list.next_cursor
