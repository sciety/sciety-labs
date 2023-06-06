import logging
from typing import Annotated, Iterable, NamedTuple, Optional, Sequence

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import requests
import starlette

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import (
    AnnotatedPaginationParameters,
    get_rss_url
)
from sciety_labs.app.utils.response import AtomResponse
from sciety_labs.models.article import ArticleSearchResultItem, iter_preprint_article_mention
from sciety_labs.providers.europe_pmc import EUROPE_PMC_PREPRINT_SERVERS
from sciety_labs.providers.search import SearchDateRange, SearchParameters, SearchSortBy
from sciety_labs.providers.semantic_scholar import SEMANTIC_SCHOLAR_SEARCH_VENUES
from sciety_labs.utils.pagination import get_url_pagination_state_for_pagination_parameters


LOGGER = logging.getLogger(__name__)


class SearchProviders:
    SEMANTIC_SCHOLAR = 'semantic_scholar'
    EUROPE_PMC = 'europe_pmc'


class UrlSearchParameters(NamedTuple):
    query: str
    evaluated_only: bool
    search_provider: str
    sort_by: str
    date_range: str


async def get_search_parameters(
    query: str = '',
    evaluated_only: bool = False,
    search_provider: str = SearchProviders.SEMANTIC_SCHOLAR,
    sort_by: str = SearchSortBy.RELEVANCE,
    date_range: str = SearchDateRange.LAST_90_DAYS
) -> UrlSearchParameters:
    return UrlSearchParameters(
        query=query,
        evaluated_only=evaluated_only,
        search_provider=search_provider,
        sort_by=sort_by,
        date_range=date_range
    )


AnnotatedSearchParameters = Annotated[
    UrlSearchParameters, Depends(get_search_parameters)
]


def create_search_router(  # pylint: disable=too-many-statements
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    article_aggregator = app_providers_and_models.article_aggregator

    router = APIRouter()

    @router.get('/search', response_class=HTMLResponse)
    def search(  # pylint: disable=too-many-arguments, too-many-locals
        request: Request,
        url_search_parameters: AnnotatedSearchParameters,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        search_result_iterable: Iterable[ArticleSearchResultItem]
        error_message: Optional[str] = None
        status_code: int = 200
        try:
            preprint_servers: Optional[Sequence[str]] = None
            search_parameters = SearchParameters(
                query=url_search_parameters.query,
                is_evaluated_only=url_search_parameters.evaluated_only,
                sort_by=url_search_parameters.sort_by,
                date_range=url_search_parameters.date_range
            )
            LOGGER.info('search_parameters: %r', search_parameters)
            if not search_parameters.query:
                search_result_iterable = []
            elif url_search_parameters.search_provider == SearchProviders.SEMANTIC_SCHOLAR:
                search_result_iterable = (
                    app_providers_and_models
                    .semantic_scholar_search_provider.iter_search_result_item(
                        search_parameters=search_parameters
                    )
                )
                preprint_servers = SEMANTIC_SCHOLAR_SEARCH_VENUES
            elif url_search_parameters.search_provider == SearchProviders.EUROPE_PMC:
                search_result_iterable = (
                    app_providers_and_models
                    .europe_pmc_provider.iter_search_result_item(
                        search_parameters=search_parameters
                    )
                )
                preprint_servers = EUROPE_PMC_PREPRINT_SERVERS
            else:
                search_result_iterable = []
            search_result_iterator = iter(search_result_iterable)
            search_result_list_with_article_meta = list(
                article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                    iter_preprint_article_mention(
                        search_result_iterator
                    ),
                    page=pagination_parameters.page,
                    items_per_page=pagination_parameters.items_per_page
                )
            )
            LOGGER.info(
                'search_result_list_with_article_meta[:1]=%r',
                search_result_list_with_article_meta[:1]
            )
        except requests.exceptions.HTTPError as exc:
            error_message = f'Error retrieving search results from provider: {exc}'
            status_code = exc.response.status_code
            search_result_list_with_article_meta = []
            search_result_iterator = iter([])
        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url,
            pagination_parameters=pagination_parameters,
            is_this_page_empty=not search_result_list_with_article_meta,
            remaining_item_iterable=search_result_iterator
        )
        return templates.TemplateResponse(
            'pages/search.html', {
                'request': request,
                'page_title': (
                    f'Search results for {search_parameters.query}'
                    if search_parameters.query else 'Search'
                ),
                'query': search_parameters.query,
                'is_search_evaluated_only': search_parameters.is_evaluated_only,
                'sort_by': search_parameters.sort_by,
                'date_range': search_parameters.date_range,
                'preprint_servers': preprint_servers,
                'error_message': error_message,
                'search_provider': url_search_parameters.search_provider,
                'search_results': search_result_list_with_article_meta,
                'pagination': url_pagination_state
            },
            status_code=status_code
        )

    @router.get('/feeds/search', response_class=HTMLResponse)
    def search_feed(  # pylint: disable=too-many-arguments, too-many-locals
        request: Request,
        pagination_parameters: AnnotatedPaginationParameters,
        query: str = '',
        evaluated_only: bool = False,
        search_provider: str = SearchProviders.SEMANTIC_SCHOLAR,
        sort_by: str = SearchSortBy.PUBLICATION_DATE,
        date_range: str = SearchDateRange.LAST_90_DAYS
    ):
        search_result_iterable: Iterable[ArticleSearchResultItem]
        error_message: Optional[str] = None
        status_code: int = 200
        try:
            preprint_servers: Optional[Sequence[str]] = None
            search_parameters = SearchParameters(
                query=query,
                is_evaluated_only=evaluated_only,
                sort_by=sort_by,
                date_range=date_range
            )
            LOGGER.info('search_parameters: %r', search_parameters)
            if not query:
                search_result_iterable = []
            elif search_provider == SearchProviders.SEMANTIC_SCHOLAR:
                search_result_iterable = (
                    app_providers_and_models
                    .semantic_scholar_search_provider.iter_search_result_item(
                        search_parameters=search_parameters
                    )
                )
                preprint_servers = SEMANTIC_SCHOLAR_SEARCH_VENUES
            elif search_provider == SearchProviders.EUROPE_PMC:
                search_result_iterable = (
                    app_providers_and_models
                    .europe_pmc_provider.iter_search_result_item(
                        search_parameters=search_parameters
                    )
                )
                preprint_servers = EUROPE_PMC_PREPRINT_SERVERS
            else:
                search_result_iterable = []
            search_result_iterator = iter(search_result_iterable)
            search_result_list_with_article_meta = list(
                article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                    iter_preprint_article_mention(
                        search_result_iterator
                    ),
                    page=pagination_parameters.page,
                    items_per_page=pagination_parameters.items_per_page
                )
            )
            LOGGER.info(
                'search_result_list_with_article_meta[:1]=%r',
                search_result_list_with_article_meta[:1]
            )
        except requests.exceptions.HTTPError as exc:
            error_message = f'Error retrieving search results from provider: {exc}'
            status_code = exc.response.status_code
            search_result_list_with_article_meta = []
            search_result_iterator = iter([])
        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url,
            pagination_parameters=pagination_parameters,
            is_this_page_empty=not search_result_list_with_article_meta,
            remaining_item_iterable=search_result_iterator
        )
        return templates.TemplateResponse(
            'pages/search-feed.html', {
                'request': request,
                'page_title': (
                    f'Search feed for {query}' if query else 'Search feed'
                ),
                'rss_url': get_rss_url(request),
                'query': query,
                'is_search_evaluated_only': evaluated_only,
                'sort_by': sort_by,
                'date_range': date_range,
                'preprint_servers': preprint_servers,
                'error_message': error_message,
                'search_provider': search_provider,
                'search_results': search_result_list_with_article_meta,
                'pagination': url_pagination_state
            },
            status_code=status_code
        )

    @router.get('/feeds/search/create', response_class=RedirectResponse)
    def create_search_feed(request: Request):
        return RedirectResponse(
            (
                request
                .url
                .remove_query_params('sort_by')
                .replace(path='/feeds/search')
            ),
            status_code=starlette.status.HTTP_302_FOUND
        )

    @router.get('/feeds/search/atom.xml', response_class=AtomResponse)
    def search_feed_atom_feed(  # pylint: disable=too-many-arguments, too-many-locals
        request: Request,
        pagination_parameters: AnnotatedPaginationParameters,
        query: str = '',
        evaluated_only: bool = False,
        search_provider: str = SearchProviders.SEMANTIC_SCHOLAR,
        sort_by: str = SearchSortBy.PUBLICATION_DATE,
        date_range: str = SearchDateRange.LAST_90_DAYS
    ):
        search_result_iterable: Iterable[ArticleSearchResultItem]
        error_message: Optional[str] = None
        status_code: int = 200
        try:
            preprint_servers: Optional[Sequence[str]] = None
            search_parameters = SearchParameters(
                query=query,
                is_evaluated_only=evaluated_only,
                sort_by=sort_by,
                date_range=date_range
            )
            LOGGER.info('search_parameters: %r', search_parameters)
            if not query:
                search_result_iterable = []
            elif search_provider == SearchProviders.SEMANTIC_SCHOLAR:
                search_result_iterable = (
                    app_providers_and_models
                    .semantic_scholar_search_provider.iter_search_result_item(
                        search_parameters=search_parameters
                    )
                )
                preprint_servers = SEMANTIC_SCHOLAR_SEARCH_VENUES
            elif search_provider == SearchProviders.EUROPE_PMC:
                search_result_iterable = (
                    app_providers_and_models
                    .europe_pmc_provider.iter_search_result_item(
                        search_parameters=search_parameters
                    )
                )
                preprint_servers = EUROPE_PMC_PREPRINT_SERVERS
            else:
                search_result_iterable = []
            search_result_iterator = iter(search_result_iterable)
            search_result_list_with_article_meta = list(
                article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                    iter_preprint_article_mention(
                        search_result_iterator
                    ),
                    page=pagination_parameters.page,
                    items_per_page=pagination_parameters.items_per_page
                )
            )
            LOGGER.info(
                'search_result_list_with_article_meta[:1]=%r',
                search_result_list_with_article_meta[:1]
            )
        except requests.exceptions.HTTPError as exc:
            error_message = f'Error retrieving search results from provider: {exc}'
            status_code = exc.response.status_code
            search_result_list_with_article_meta = []
            search_result_iterator = iter([])
        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url,
            pagination_parameters=pagination_parameters,
            is_this_page_empty=not search_result_list_with_article_meta,
            remaining_item_iterable=search_result_iterator
        )
        return templates.TemplateResponse(
            'pages/search-feed.atom.xml', {
                'request': request,
                'page_title': (
                    f'Search feed for {query}' if query else 'Search feed'
                ),
                'query': query,
                'is_search_evaluated_only': evaluated_only,
                'sort_by': sort_by,
                'date_range': date_range,
                'preprint_servers': preprint_servers,
                'error_message': error_message,
                'search_provider': search_provider,
                'search_results': search_result_list_with_article_meta,
                'pagination': url_pagination_state
            },
            media_type=AtomResponse.media_type,
            status_code=status_code
        )

    return router
