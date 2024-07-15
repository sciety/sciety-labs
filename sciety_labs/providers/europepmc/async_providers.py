import logging
from typing import AsyncIterable

from sciety_labs.models.article import ArticleSearchResultItem
from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider
from sciety_labs.providers.europepmc.utils import (
    START_CURSOR,
    CursorBasedArticleSearchResultList,
    _iter_article_search_result_item_from_search_response_json,
    get_query_with_additional_filters
)
from sciety_labs.providers.search import (
    SearchParameters,
    AsyncSearchProvider
)


LOGGER = logging.getLogger(__name__)


class AsyncEuropePmcProvider(AsyncRequestsProvider, AsyncSearchProvider):
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
            headers=self.headers,
            timeout=self.timeout
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
    ) -> AsyncIterable[ArticleSearchResultItem]:
        cursor = START_CURSOR
        while True:
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
