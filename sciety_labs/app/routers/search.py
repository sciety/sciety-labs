import hashlib
import logging
from datetime import date, datetime
from typing import Annotated, AsyncIterator, Optional, Sequence, Union
import aiohttp
from attr import dataclass

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import starlette

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import (
    AnnotatedPaginationParameters,
    get_page_title,
    get_rss_url
)
from sciety_labs.app.utils.response import AtomResponse
from sciety_labs.config.search_feed_config import SearchFeedConfig, SearchFeedsConfig
from sciety_labs.models.article import ArticleSearchResultItem, async_iter_preprint_article_mention
from sciety_labs.models.image import ObjectImages
from sciety_labs.providers.europepmc.utils import EUROPE_PMC_PREPRINT_SERVERS
from sciety_labs.providers.papers.async_papers import PageNumberBasedPaginationParameters
from sciety_labs.providers.search import SearchDateRange, SearchParameters, SearchSortBy
from sciety_labs.providers.semantic_scholar.utils import SEMANTIC_SCHOLAR_SEARCH_VENUES
from sciety_labs.utils.aio import get_exception_status_code
from sciety_labs.utils.async_utils import async_iter_sync_iterable, get_list_for_async_iterable
from sciety_labs.utils.datetime import get_date_as_utc_timestamp, get_utcnow
from sciety_labs.utils.pagination import (
    EMPTY_URL_PAGINATION_STATE,
    UrlPaginationParameters,
    UrlPaginationState,
    async_get_url_pagination_state_for_pagination_parameters,
    get_url_pagination_state_for_pagination_parameters
)


LOGGER = logging.getLogger(__name__)


GENERIC_SEARCH_FEED_PAGE_DESCRIPTION = 'Keep up to date with the latest preprint activity'


MIN_QUERY_LENGTH = 3


class SearchProviders:
    SCIETY_LABS = 'sciety_labs'
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


@dataclass
class SearchFeedParameters:
    search_parameters: UrlSearchParameters
    page_title: str
    page_description: str
    feed_images: Optional[ObjectImages] = None


def get_default_search_feed_parameters(
    search_parameters: UrlSearchParameters
) -> SearchFeedParameters:
    return SearchFeedParameters(
        search_parameters=search_parameters,
        page_title=(
            f'Search feed for {search_parameters.query}'
            if search_parameters.query else 'Search feed'
        ),
        page_description=GENERIC_SEARCH_FEED_PAGE_DESCRIPTION
    )


def get_search_feed_parameters_for_search_feed_config(
    search_feed_config: SearchFeedConfig
) -> SearchFeedParameters:
    return SearchFeedParameters(
        search_parameters=UrlSearchParameters(
            query=search_feed_config.query,
            is_evaluated_only=False,
            sort_by=SearchSortBy.PUBLICATION_DATE,
            date_range=SearchDateRange.LAST_90_DAYS,
            search_provider=SearchProviders.EUROPE_PMC
        ),
        page_title=search_feed_config.title,
        page_description=search_feed_config.description,
        feed_images=ObjectImages(
            image_url=search_feed_config.image_url,
            wide_image_url=search_feed_config.wide_image_url
        )
    )


async def get_search_parameters(
    query: str = '',
    evaluated_only: bool = False,
    search_provider: str = SearchProviders.SCIETY_LABS,
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
    technical_error_message: Optional[str] = None
    preprint_servers: Optional[Sequence[str]] = None
    status_code: int = 200


async def get_search_result_page_using_iterator(
    app_providers_and_models: AppProvidersAndModels,
    request: Request,
    search_parameters: AnnotatedSearchParameters,
    pagination_parameters: AnnotatedPaginationParameters
) -> SearchResultPage:
    search_result_iterator: AsyncIterator[ArticleSearchResultItem]
    preprint_servers: Optional[Sequence[str]] = None
    LOGGER.info('search_parameters: %r', search_parameters)
    if not search_parameters.query:
        search_result_iterator = async_iter_sync_iterable([])
    elif search_parameters.search_provider == SearchProviders.SEMANTIC_SCHOLAR:
        search_result_iterator = (
            app_providers_and_models
            .semantic_scholar_search_provider.iter_search_result_item(
                search_parameters=search_parameters
            )
        )
        preprint_servers = SEMANTIC_SCHOLAR_SEARCH_VENUES
    elif search_parameters.search_provider == SearchProviders.EUROPE_PMC:
        search_result_iterator = (
            app_providers_and_models
            .europe_pmc_provider.iter_search_result_item(
                search_parameters=search_parameters
            )
        )
        preprint_servers = EUROPE_PMC_PREPRINT_SERVERS
    else:
        search_result_iterator = async_iter_sync_iterable([])
    search_result_list_with_article_meta = await get_list_for_async_iterable(
        app_providers_and_models
        .article_aggregator
        .async_iter_page_article_mention_with_article_meta_and_stats(
            async_iter_preprint_article_mention(
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
    url_pagination_state = await async_get_url_pagination_state_for_pagination_parameters(
        url=request.url,
        pagination_parameters=pagination_parameters,
        is_this_page_empty=not search_result_list_with_article_meta,
        remaining_item_iterable=search_result_iterator
    )
    return SearchResultPage(
        search_result_list_with_article_meta=search_result_list_with_article_meta,
        preprint_servers=preprint_servers,
        url_pagination_state=url_pagination_state
    )


async def get_search_result_page_using_pagination(
    app_providers_and_models: AppProvidersAndModels,
    request: Request,
    search_parameters: AnnotatedSearchParameters,
    pagination_parameters: AnnotatedPaginationParameters
) -> SearchResultPage:
    assert search_parameters.search_provider == SearchProviders.SCIETY_LABS
    preprint_servers: Optional[Sequence[str]] = None
    search_results_list = await (
        app_providers_and_models
        .async_paper_provider
        .get_preprints_for_search_results_list(
            query=search_parameters.query,
            evaluated_only=search_parameters.is_evaluated_only,
            from_publication_date=SearchDateRange.get_from_date(search_parameters.date_range),
            pagination_parameters=PageNumberBasedPaginationParameters(
                page=pagination_parameters.page,
                items_per_page=pagination_parameters.items_per_page
            )
        )
    )
    LOGGER.info('search_results_list: %r', search_results_list)
    search_result_list_with_article_meta = list(
        app_providers_and_models
        .article_aggregator
        .iter_page_article_mention_with_article_meta_and_stats(
            search_results_list.items,
            page=1,  # pagination is handled by service
            items_per_page=pagination_parameters.items_per_page
        )
    )
    LOGGER.info(
        'search_result_list_with_article_meta[:1]=%r',
        search_result_list_with_article_meta[:1]
    )
    url_pagination_state = get_url_pagination_state_for_pagination_parameters(
        url=request.url,
        pagination_parameters=pagination_parameters,
        is_this_page_empty=not search_result_list_with_article_meta,
        item_count=search_results_list.total
    )
    return SearchResultPage(
        search_result_list_with_article_meta=search_result_list_with_article_meta,
        preprint_servers=preprint_servers,
        url_pagination_state=url_pagination_state
    )


def get_empty_search_result_page() -> SearchResultPage:
    return SearchResultPage(
        search_result_list_with_article_meta=[],
        preprint_servers=None,
        url_pagination_state=EMPTY_URL_PAGINATION_STATE
    )


def get_search_result_error_page(exception: Exception) -> SearchResultPage:
    if isinstance(exception, aiohttp.ClientError):
        error_message = 'Error retrieving search results from provider'
    else:
        error_message = str(exception)
    if not error_message:
        error_message = 'Unknown error'
    technical_error_message = repr(exception)
    status_code = get_exception_status_code(exception) or 500
    return SearchResultPage(
        search_result_list_with_article_meta=[],
        preprint_servers=None,
        url_pagination_state=EMPTY_URL_PAGINATION_STATE,
        error_message=error_message,
        technical_error_message=technical_error_message,
        status_code=status_code
    )


async def get_search_result_page(
    app_providers_and_models: AppProvidersAndModels,
    request: Request,
    search_parameters: AnnotatedSearchParameters,
    pagination_parameters: AnnotatedPaginationParameters
) -> SearchResultPage:
    if not search_parameters.query:
        return get_empty_search_result_page()
    try:
        if len(search_parameters.query) < MIN_QUERY_LENGTH:
            raise AssertionError(
                f'Search query should be at least {MIN_QUERY_LENGTH} characters long'
            )
        if search_parameters.search_provider == SearchProviders.SCIETY_LABS:
            # Note: We don't need to use the less efficient iterator,
            #   if the search provider filters and sorts results at source
            return await get_search_result_page_using_pagination(
                app_providers_and_models=app_providers_and_models,
                request=request,
                search_parameters=search_parameters,
                pagination_parameters=pagination_parameters
            )
        return await get_search_result_page_using_iterator(
            app_providers_and_models=app_providers_and_models,
            request=request,
            search_parameters=search_parameters,
            pagination_parameters=pagination_parameters
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return get_search_result_error_page(exception=exc)


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
        'technical_error_message': search_result_page.technical_error_message,
        'search_results': search_result_page.search_result_list_with_article_meta,
        'pagination': search_result_page.url_pagination_state
    }


def create_search_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates,
    search_feeds_config: SearchFeedsConfig
):
    router = APIRouter()

    @router.get('/search', response_class=HTMLResponse)
    async def search(
        request: Request,
        search_parameters: AnnotatedSearchParameters,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        search_result_page = await get_search_result_page(
            app_providers_and_models=app_providers_and_models,
            request=request,
            search_parameters=search_parameters,
            pagination_parameters=pagination_parameters
        )
        LOGGER.info('search_result_page: %r', search_result_page)
        return templates.TemplateResponse(
            request=request,
            name='pages/search.html',
            context={
                **get_search_parameters_template_parameters(search_parameters),
                **get_search_result_template_parameters(search_result_page),
                'min_query_length': MIN_QUERY_LENGTH,
                'page_title': (
                    f'Search results for {search_parameters.query}'
                    if search_parameters.query else 'Search'
                )
            },
            status_code=search_result_page.status_code
        )

    async def _render_search_feed(
        request: Request,
        search_feed_parameters: SearchFeedParameters,
        pagination_parameters: UrlPaginationParameters
    ):
        search_result_page = await get_search_result_page(
            app_providers_and_models=app_providers_and_models,
            request=request,
            search_parameters=search_feed_parameters.search_parameters,
            pagination_parameters=pagination_parameters
        )
        return templates.TemplateResponse(
            request=request,
            name='pages/search-feed.html',
            context={
                **get_search_parameters_template_parameters(
                    search_feed_parameters.search_parameters
                ),
                **get_search_result_template_parameters(search_result_page),
                'min_query_length': MIN_QUERY_LENGTH,
                'page_title': search_feed_parameters.page_title,
                'page_description': search_feed_parameters.page_description,
                'page_images': search_feed_parameters.feed_images,
                'rss_url': get_rss_url(request)
            },
            status_code=search_result_page.status_code
        )

    async def _render_search_feed_atom_xml(
        request: Request,
        search_feed_parameters: SearchFeedParameters,
        pagination_parameters: UrlPaginationParameters
    ):
        search_result_page = await get_search_result_page(
            app_providers_and_models=app_providers_and_models,
            request=request,
            search_parameters=search_feed_parameters.search_parameters,
            pagination_parameters=pagination_parameters
        )
        return templates.TemplateResponse(
            request=request,
            name='pages/search-feed.atom.xml',
            context={
                **get_search_parameters_template_parameters(
                    search_feed_parameters.search_parameters
                ),
                **get_search_result_template_parameters(search_result_page),
                'last_updated_timestamp': get_rss_updated_timestamp(
                    search_result_page.search_result_list_with_article_meta
                ),
                'search_parameters_hash': search_feed_parameters.search_parameters.get_hash(),
                'page_title': search_feed_parameters.page_title,
                'page_description': search_feed_parameters.page_description,
                'page_images': search_feed_parameters.feed_images
            },
            media_type=AtomResponse.media_type,
            status_code=search_result_page.status_code
        )

    @router.get('/feeds', response_class=HTMLResponse)
    async def search_feeds(
        request: Request
    ):
        return templates.TemplateResponse(
            request=request,
            name='pages/search-feeds.html',
            context={
                'page_title': get_page_title('Feeds'),
                'search_feeds': search_feeds_config.feeds_by_slug.values()
            }
        )

    @router.get('/feeds/search', response_class=HTMLResponse)
    async def search_feed(
        request: Request,
        search_parameters: AnnotatedSearchParameters,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        return await _render_search_feed(
            request=request,
            search_feed_parameters=get_default_search_feed_parameters(search_parameters),
            pagination_parameters=pagination_parameters
        )

    @router.get('/feeds/search/create', response_class=RedirectResponse)
    async def create_search_feed(request: Request):
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
    async def search_feed_atom_feed(
        request: Request,
        search_parameters: AnnotatedSearchParameters,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        return await _render_search_feed_atom_xml(
            request=request,
            search_feed_parameters=get_default_search_feed_parameters(search_parameters),
            pagination_parameters=pagination_parameters
        )

    @router.get('/feeds/by-name/{slug}', response_class=HTMLResponse)
    async def search_feed_by_name(
        request: Request,
        pagination_parameters: AnnotatedPaginationParameters,
        slug: str
    ):
        try:
            search_feed_config = search_feeds_config.feeds_by_slug[slug]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Feed not found") from exc
        search_parameters = get_search_feed_parameters_for_search_feed_config(search_feed_config)
        return await _render_search_feed(
            request=request,
            search_feed_parameters=search_parameters,
            pagination_parameters=pagination_parameters
        )

    @router.get('/feeds/by-name/{slug}/atom.xml', response_class=AtomResponse)
    async def search_feed_by_name_atom_feed(
        request: Request,
        pagination_parameters: AnnotatedPaginationParameters,
        slug: str
    ):
        try:
            search_feed_config = search_feeds_config.feeds_by_slug[slug]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Feed not found") from exc
        search_parameters = get_search_feed_parameters_for_search_feed_config(search_feed_config)
        return await _render_search_feed_atom_xml(
            request=request,
            search_feed_parameters=search_parameters,
            pagination_parameters=pagination_parameters
        )

    return router
