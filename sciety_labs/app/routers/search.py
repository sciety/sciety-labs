import logging
from typing import Iterable, Optional, Sequence

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import (
    AnnotatedPaginationParameters
)
from sciety_labs.models.article import ArticleSearchResultItem, iter_preprint_article_mention
from sciety_labs.providers.europe_pmc import EUROPE_PMC_PREPRINT_SERVERS
from sciety_labs.providers.search import SearchDateRange, SearchParameters, SearchSortBy
from sciety_labs.providers.semantic_scholar import SEMANTIC_SCHOLAR_SEARCH_VENUES
from sciety_labs.utils.pagination import get_url_pagination_state_for_pagination_parameters


LOGGER = logging.getLogger(__name__)


class SearchProviders:
    SEMANTIC_SCHOLAR = 'semantic_scholar'
    EUROPE_PMC = 'europe_pmc'


def create_search_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    article_aggregator = app_providers_and_models.article_aggregator

    router = APIRouter()

    @router.get('/search', response_class=HTMLResponse)
    def search(  # pylint: disable=too-many-arguments, too-many-locals
        request: Request,
        pagination_parameters: AnnotatedPaginationParameters,
        query: str = '',
        evaluated_only: bool = False,
        search_provider: str = SearchProviders.SEMANTIC_SCHOLAR,
        sort_by: str = SearchSortBy.RELEVANCE,
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
            'pages/search.html', {
                'request': request,
                'page_title': (
                    f'Search results for {query}' if query else 'Search'
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
            status_code=status_code
        )

    return router
