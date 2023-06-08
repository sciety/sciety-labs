import hashlib
import logging
from datetime import date, datetime
from typing import Annotated, Iterable, Optional, Sequence, Union
from attr import dataclass

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
from sciety_labs.models.image import ObjectImages
from sciety_labs.providers.europe_pmc import EUROPE_PMC_PREPRINT_SERVERS
from sciety_labs.providers.search import SearchDateRange, SearchParameters, SearchSortBy
from sciety_labs.providers.semantic_scholar import SEMANTIC_SCHOLAR_SEARCH_VENUES
from sciety_labs.utils.datetime import get_date_as_utc_timestamp, get_utcnow
from sciety_labs.utils.pagination import (
    UrlPaginationState,
    get_url_pagination_state_for_pagination_parameters
)


LOGGER = logging.getLogger(__name__)


GENERIC_SEARCH_FEED_PAGE_DESCRIPTION = 'Keep up to date with the latest preprint activity'


class SearchProviders:
    SEMANTIC_SCHOLAR = 'semantic_scholar'
    EUROPE_PMC = 'europe_pmc'


@dataclass
class UrlSearchParameters(SearchParameters):
    search_provider: str = SearchProviders.SEMANTIC_SCHOLAR

    def get_hash(self) -> str:
        return hashlib.md5(
            '|'.join([
                self.query,
                self.date_range
            ]).encode('utf-8')
        ).hexdigest()


async def get_search_parameters(
    query: str = '',
    evaluated_only: bool = False,
    search_provider: str = SearchProviders.SEMANTIC_SCHOLAR,
    sort_by: str = SearchSortBy.RELEVANCE,
    date_range: str = SearchDateRange.LAST_90_DAYS
) -> UrlSearchParameters:
    return UrlSearchParameters(
        query=query,
        is_evaluated_only=evaluated_only,
        search_provider=search_provider,
        sort_by=sort_by,
        date_range=date_range
    )


AnnotatedSearchParameters = Annotated[
    UrlSearchParameters, Depends(get_search_parameters)
]


@dataclass
class SearchResultPage:
    search_result_list_with_article_meta: Sequence[ArticleSearchResultItem]
    url_pagination_state: UrlPaginationState
    error_message: Optional[str] = None
    preprint_servers: Optional[Sequence[str]] = None
    status_code: int = 200


def get_search_result_page(
    app_providers_and_models: AppProvidersAndModels,
    request: Request,
    search_parameters: AnnotatedSearchParameters,
    pagination_parameters: AnnotatedPaginationParameters
) -> SearchResultPage:
    search_result_iterable: Iterable[ArticleSearchResultItem]
    error_message: Optional[str] = None
    status_code: int = 200
    try:
        preprint_servers: Optional[Sequence[str]] = None
        LOGGER.info('search_parameters: %r', search_parameters)
        if not search_parameters.query:
            search_result_iterable = []
        elif search_parameters.search_provider == SearchProviders.SEMANTIC_SCHOLAR:
            search_result_iterable = (
                app_providers_and_models
                .semantic_scholar_search_provider.iter_search_result_item(
                    search_parameters=search_parameters
                )
            )
            preprint_servers = SEMANTIC_SCHOLAR_SEARCH_VENUES
        elif search_parameters.search_provider == SearchProviders.EUROPE_PMC:
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
            app_providers_and_models
            .article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
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
    return SearchResultPage(
        search_result_list_with_article_meta=search_result_list_with_article_meta,
        preprint_servers=preprint_servers,
        url_pagination_state=url_pagination_state,
        error_message=error_message,
        status_code=status_code
    )


def get_rss_updated_timestamp(
    search_result_list_with_article_meta: Sequence[ArticleSearchResultItem]
) -> Union[date, datetime]:
    publication_dates = [
        article_mention.article_meta.published_date
        for article_mention in search_result_list_with_article_meta
        if article_mention.article_meta and article_mention.article_meta.published_date
    ]
    if not publication_dates:
        return get_utcnow()
    return get_date_as_utc_timestamp(max(publication_dates))


def get_search_parameters_template_parameters(
    search_parameters: AnnotatedSearchParameters
) -> dict:
    return {
        'query': search_parameters.query,
        'is_search_evaluated_only': search_parameters.is_evaluated_only,
        'sort_by': search_parameters.sort_by,
        'date_range': search_parameters.date_range,
        'search_provider': search_parameters.search_provider
    }


def get_search_result_template_parameters(
    search_result_page: SearchResultPage
) -> dict:
    return {
        'preprint_servers': search_result_page.preprint_servers,
        'error_message': search_result_page.error_message,
        'search_results': search_result_page.search_result_list_with_article_meta,
        'pagination': search_result_page.url_pagination_state
    }


def create_search_router(  # pylint: disable=too-many-statements
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    router = APIRouter()

    @router.get('/search', response_class=HTMLResponse)
    def search(  # pylint: disable=too-many-arguments, too-many-locals
        request: Request,
        search_parameters: AnnotatedSearchParameters,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        search_result_page = get_search_result_page(
            app_providers_and_models=app_providers_and_models,
            request=request,
            search_parameters=search_parameters,
            pagination_parameters=pagination_parameters
        )
        return templates.TemplateResponse(
            'pages/search.html', {
                **get_search_parameters_template_parameters(search_parameters),
                **get_search_result_template_parameters(search_result_page),
                'request': request,
                'page_title': (
                    f'Search results for {search_parameters.query}'
                    if search_parameters.query else 'Search'
                )
            },
            status_code=search_result_page.status_code
        )

    @router.get('/feeds/search', response_class=HTMLResponse)
    def search_feed(  # pylint: disable=too-many-arguments, too-many-locals
        request: Request,
        search_parameters: AnnotatedSearchParameters,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        search_result_page = get_search_result_page(
            app_providers_and_models=app_providers_and_models,
            request=request,
            search_parameters=search_parameters,
            pagination_parameters=pagination_parameters
        )
        return templates.TemplateResponse(
            'pages/search-feed.html', {
                **get_search_parameters_template_parameters(search_parameters),
                **get_search_result_template_parameters(search_result_page),
                'request': request,
                'page_title': (
                    f'Search feed for {search_parameters.query}'
                    if search_parameters.query else 'Search feed'
                ),
                'page_description': GENERIC_SEARCH_FEED_PAGE_DESCRIPTION,
                'rss_url': get_rss_url(request)
            },
            status_code=search_result_page.status_code
        )

    @router.get('/feeds/search/create', response_class=RedirectResponse)
    def create_search_feed(request: Request):
        return RedirectResponse(
            (
                request
                .url
                .remove_query_params('sort_by')
                .include_query_params(sort_by=SearchSortBy.PUBLICATION_DATE)
                .replace(path='/feeds/search')
            ),
            status_code=starlette.status.HTTP_302_FOUND
        )

    @router.get('/feeds/search/atom.xml', response_class=AtomResponse)
    def search_feed_atom_feed(  # pylint: disable=too-many-arguments, too-many-locals
        request: Request,
        search_parameters: AnnotatedSearchParameters,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        search_result_page = get_search_result_page(
            app_providers_and_models=app_providers_and_models,
            request=request,
            search_parameters=search_parameters,
            pagination_parameters=pagination_parameters
        )
        return templates.TemplateResponse(
            'pages/search-feed.atom.xml', {
                **get_search_parameters_template_parameters(search_parameters),
                **get_search_result_template_parameters(search_result_page),
                'request': request,
                'last_updated_timestamp': get_rss_updated_timestamp(
                    search_result_page.search_result_list_with_article_meta
                ),
                'search_parameters_hash': search_parameters.get_hash(),
                'page_title': (
                    f'Search feed for {search_parameters.query}'
                    if search_parameters.query else 'Search feed'
                ),
                'page_description': GENERIC_SEARCH_FEED_PAGE_DESCRIPTION
            },
            media_type=AtomResponse.media_type,
            status_code=search_result_page.status_code
        )

    @router.get('/feeds/by-name/plant-science', response_class=HTMLResponse)
    def search_feed_by_name(
        request: Request,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        search_parameters = UrlSearchParameters(
            query=(
                '(Botany) OR (Plant biology) OR (Plant physiology) OR (Plant genetics) OR (Plant taxonomy) OR (Plant anatomy) OR (Plant ecology) OR (Plant evolution) OR (Plant biochemistry) OR (Plant molecular biology) OR (Plant biotechnology) OR (Plant growth and development) OR (Plant reproduction) OR (Plant nutrition) OR (Plant hormones) OR (Plant diseases) OR (Plant breeding) OR (Plant stress responses) OR (Plant symbiosis)'  # noqa pylint: disable=line-too-long
            ),
            is_evaluated_only=False,
            sort_by=SearchSortBy.PUBLICATION_DATE,
            date_range=SearchDateRange.LAST_90_DAYS,
            search_provider=SearchProviders.EUROPE_PMC
        )
        search_result_page = get_search_result_page(
            app_providers_and_models=app_providers_and_models,
            request=request,
            search_parameters=search_parameters,
            pagination_parameters=pagination_parameters
        )
        return templates.TemplateResponse(
            'pages/search-feed.html', {
                **get_search_parameters_template_parameters(search_parameters),
                **get_search_result_template_parameters(search_result_page),
                'request': request,
                'feed_images': ObjectImages(
                    'https://storage.googleapis.com/public-article-images/manually-uploaded/search-feeds/2023-06-08-plant%20science%2C%20water%20colour%20painting-2.jpeg'  # noqa pylint: disable=line-too-long
                ),
                'page_title': 'Plant Science',
                'page_description': GENERIC_SEARCH_FEED_PAGE_DESCRIPTION
            },
            status_code=search_result_page.status_code
        )

    return router