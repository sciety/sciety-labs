import dataclasses
import logging
from typing import Iterable, Mapping, Optional, Sequence

from sciety_labs.models.article import ArticleMetaData, ArticleSearchResultItem
from sciety_labs.providers.requests_provider import RequestsProvider
from sciety_labs.providers.search import SearchParameters, SearchProvider, SearchSortBy


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


def get_query_with_additional_filters(
    query: str,
    is_evaluated_only: bool,
    sort_by: str = SearchSortBy.RELEVANCE
) -> str:
    preprint_servers_query = get_preprint_servers_query(EUROPE_PMC_PREPRINT_SERVERS)
    result = f'({preprint_servers_query})'
    if is_evaluated_only:
        result += ' (LABS_PUBS:"2112")'
    result += f' ({query})'
    if sort_by == SearchSortBy.PUBLICATION_DATE:
        result += ' sort_date:y'
    return result


class EuropePmcProvider(RequestsProvider, SearchProvider):
    def get_search_result_list(  # pylint: disable=too-many-arguments
        self,
        query: str,
        is_evaluated_only: bool,
        sort_by: str = SearchSortBy.RELEVANCE,
        additional_search_parameters: Optional[Mapping[str, str]] = None,
        cursor: str = START_CURSOR,
        limit: int = DEFAULT_EUROPE_PMC_SEARCH_RESULT_LIMIT
    ) -> CursorBasedArticleSearchResultList:
        request_params = {
            **(additional_search_parameters if additional_search_parameters else {}),
            'query': get_query_with_additional_filters(
                query,
                is_evaluated_only=is_evaluated_only,
                sort_by=sort_by
            ),
            'format': 'json',
            'cursorMark': cursor,
            'pageSize': str(limit)
        }
        LOGGER.info('Europe PMC search, request_params=%r', request_params)
        response = self.requests_session.get(
            'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
            params=request_params,
            headers=self.headers,
            timeout=self.timeout
        )
        LOGGER.info('Europe PMC search, url=%r', response.request.url)
        response.raise_for_status()
        response_json = response.json()
        LOGGER.debug('Europe PMC search, response_json=%r', response_json)
        return CursorBasedArticleSearchResultList(
            items=list(_iter_article_search_result_item_from_search_response_json(
                response_json
            )),
            cursor=response_json['request']['cursorMark'],
            total=response_json['hitCount'],
            next_cursor=response_json.get('nextCursorMark')
        )

    def iter_search_result_item(
        self,
        search_parameters: SearchParameters
    ) -> Iterable[ArticleSearchResultItem]:
        cursor = START_CURSOR
        while True:
            search_result_list = self.get_search_result_list(
                query=search_parameters.query,
                is_evaluated_only=search_parameters.is_evaluated_only,
                sort_by=search_parameters.sort_by,
                additional_search_parameters=search_parameters.additional_search_parameters,
                cursor=cursor,
                limit=search_parameters.items_per_page
            )
            yield from search_result_list.items
            if not search_result_list.next_cursor or search_result_list.next_cursor == cursor:
                LOGGER.info('no more search results (no next cursor)')
                break
            cursor = search_result_list.next_cursor
