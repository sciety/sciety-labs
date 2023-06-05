from http.client import HTTPException
import logging
from typing import Iterable, Optional, Sequence

import requests

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import markupsafe

import bleach
from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.app_update_manager import AppUpdateManager
from sciety_labs.app.routers.lists import create_lists_router
from sciety_labs.app.utils.common import get_page_title
from sciety_labs.app.utils.response import AtomResponse
from sciety_labs.config.site_config import get_site_config_from_environment_variables

from sciety_labs.models.article import (
    ArticleMention,
    ArticleSearchResultItem,
    iter_preprint_article_mention
)

from sciety_labs.models.lists import OwnerMetaData, OwnerTypes
from sciety_labs.providers.europe_pmc import EUROPE_PMC_PREPRINT_SERVERS
from sciety_labs.providers.search import SearchDateRange, SearchParameters, SearchSortBy
from sciety_labs.providers.semantic_scholar import (
    DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS,
    SEMANTIC_SCHOLAR_SEARCH_VENUES
)
from sciety_labs.utils.datetime import (
    get_date_as_display_format,
    get_date_as_isoformat,
    get_timestamp_as_isoformat
)
from sciety_labs.utils.pagination import (
    get_page_iterable,
    get_url_pagination_state_for_url
)
from sciety_labs.utils.text import remove_markup_or_none


LOGGER = logging.getLogger(__name__)


ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'bold',
    'code',
    'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
    'h1', 'h2', 'h3', 'p', 'img', 'video', 'div',
    'p', 'br', 'span', 'hr', 'src', 'class',
    'section', 'sub', 'sup'
]


DEFAULT_ITEMS_PER_PAGE = 10

# Note: we are aiming to include all of the recommendations in the RSS
#   because RSS clients may sort by publication date, whereas the recommendations
#   are otherwise sorted by relevancy
DEFAULT_ARTICLE_RECOMMENDATION_RSS_ITEM_COUNT = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS


class SearchProviders:
    SEMANTIC_SCHOLAR = 'semantic_scholar'
    EUROPE_PMC = 'europe_pmc'


def get_owner_url(owner: OwnerMetaData) -> Optional[str]:
    if owner.owner_type == OwnerTypes.USER and owner.twitter_handle:
        return f'https://sciety.org/users/{owner.twitter_handle}'
    if owner.owner_type == OwnerTypes.GROUP and owner.slug:
        return f'https://sciety.org/groups/{owner.slug}'
    return None


def get_sanitized_string_as_safe_markup(text: str) -> markupsafe.Markup:
    return markupsafe.Markup(bleach.clean(text, tags=ALLOWED_TAGS))


def create_app():  # pylint: disable=too-many-locals, too-many-statements
    site_config = get_site_config_from_environment_variables()
    LOGGER.info('site_config: %r', site_config)

    update_interval_in_secs = 60 * 60  # 1 hour
    min_article_count = 2

    app_providers_and_models = AppProvidersAndModels()

    app_update_manager = AppUpdateManager(
        app_providers_and_models=app_providers_and_models
    )
    app_update_manager.start(update_interval_in_secs=update_interval_in_secs)

    LOGGER.info('Preloading data')
    app_update_manager.check_or_reload_data()

    templates = Jinja2Templates(directory='templates')
    templates.env.filters['sanitize'] = get_sanitized_string_as_safe_markup
    templates.env.filters['date_isoformat'] = get_date_as_isoformat
    templates.env.filters['date_display_format'] = get_date_as_display_format
    templates.env.filters['timestamp_isoformat'] = get_timestamp_as_isoformat
    templates.env.globals['site_config'] = site_config

    app = FastAPI()
    app.mount('/static', StaticFiles(directory='static', html=False), name='static')

    app.include_router(create_lists_router(
        app_providers_and_models=app_providers_and_models,
        min_article_count=min_article_count,
        templates=templates
    ))

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            'errors/404.html', {
                'request': request,
                'page_title': get_page_title('Page not found'),
                'exception': exception
            },
            status_code=404
        )

    @app.exception_handler(500)
    async def server_error_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            'errors/500.html', {
                'request': request,
                'page_title': get_page_title('Something went wrong'),
                'exception': exception
            },
            status_code=500
        )

    @app.get('/', response_class=HTMLResponse)
    def index(request: Request):
        user_list_summary_data_list = list(
            app_providers_and_models
            .google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                app_providers_and_models.lists_model.get_most_active_user_lists(
                    top_n=3,
                    min_article_count=min_article_count
                )
            )
        )
        LOGGER.info('user_list_summary_data_list: %r', user_list_summary_data_list)
        group_list_summary_data_list = list(
            app_providers_and_models
            .google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                app_providers_and_models.lists_model.get_most_active_group_lists(
                    top_n=3,
                    min_article_count=min_article_count
                )
            )
        )
        LOGGER.info('group_list_summary_data_list: %r', group_list_summary_data_list)
        return templates.TemplateResponse(
            'pages/index.html', {
                'request': request,
                'user_lists': user_list_summary_data_list,
                'group_lists': group_list_summary_data_list
            }
        )

    def _get_page_article_mention_with_article_meta_for_article_mention_iterable(
        article_mention_iterable: Iterable[ArticleMention],
        page: int,
        items_per_page: Optional[int]
    ) -> Iterable[ArticleMention]:
        article_mention_iterable = (
            app_providers_and_models
            .evaluation_stats_model.iter_article_mention_with_article_stats(
                article_mention_iterable
            )
        )
        article_mention_with_article_meta = (
            app_providers_and_models
            .crossref_metadata_provider.iter_article_mention_with_article_meta(
                get_page_iterable(
                    article_mention_iterable, page=page, items_per_page=items_per_page
                )
            )
        )
        article_mention_with_article_meta = (
            app_providers_and_models
            .google_sheet_article_image_provider.iter_article_mention_with_article_image_url(
                article_mention_with_article_meta
            )
        )
        article_mention_with_article_meta = list(article_mention_with_article_meta)
        LOGGER.debug(
            'article_mention_with_article_meta[:1]=%r', article_mention_with_article_meta[:1]
        )
        return article_mention_with_article_meta

    @app.get('/lists/by-id/{list_id}', response_class=HTMLResponse)
    def list_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        enable_pagination: bool = True
    ):
        list_summary_data = (
            app_providers_and_models.lists_model.get_list_summary_data_by_list_id(list_id)
        )
        LOGGER.info('list_summary_data: %r', list_summary_data)
        list_images = (
            app_providers_and_models
            .google_sheet_list_image_provider.get_list_images_by_list_id(list_id)
        )
        LOGGER.info('list_images: %r', list_images)
        item_count = list_summary_data.article_count
        article_mention_with_article_meta = (
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                app_providers_and_models.lists_model.iter_article_mentions_by_list_id(list_id),
                page=page,
                items_per_page=items_per_page
            )
        )

        url_pagination_state = get_url_pagination_state_for_url(
            url=request.url,
            page=page,
            items_per_page=items_per_page,
            item_count=item_count,
            enable_pagination=enable_pagination
        )
        rss_url = (
            request
            .url
            .remove_query_params(['page', 'items_per_page', 'enable_pagination'])
            .replace(
                path=request.url.path + '/atom.xml'
            )
        )
        return templates.TemplateResponse(
            'pages/list-by-sciety-list-id.html', {
                'request': request,
                'page_title': get_page_title(list_summary_data.list_meta.list_name),
                'page_description': remove_markup_or_none(
                    list_summary_data.list_meta.list_description
                ),
                'rss_url': rss_url,
                'owner_url': get_owner_url(list_summary_data.owner),
                'list_summary_data': list_summary_data,
                'list_images': list_images,
                'article_list_content': article_mention_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    @app.get('/lists/by-id/{list_id}/atom.xml', response_class=AtomResponse)
    def list_atom_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: Optional[int] = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1
    ):
        list_summary_data = (
            app_providers_and_models.lists_model.get_list_summary_data_by_list_id(list_id)
        )
        LOGGER.info('list_summary_data: %r', list_summary_data)
        article_mention_with_article_meta = (
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                app_providers_and_models.lists_model.iter_article_mentions_by_list_id(list_id),
                page=page,
                items_per_page=items_per_page
            )
        )
        return templates.TemplateResponse(
            'pages/list-by-sciety-list-id.atom.xml', {
                'request': request,
                'list_summary_data': list_summary_data,
                'article_list_content': article_mention_with_article_meta
            },
            media_type=AtomResponse.media_type
        )

    @app.get('/lists/by-id/{list_id}/article-recommendations', response_class=HTMLResponse)
    def article_recommendations_by_sciety_list_id(  # pylint: disable=too-many-arguments
        request: Request,
        list_id: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS,
        enable_pagination: bool = True
    ):
        list_summary_data = (
            app_providers_and_models.lists_model.get_list_summary_data_by_list_id(list_id)
        )
        all_article_recommendations = list(
            iter_preprint_article_mention(
                app_providers_and_models
                .semantic_scholar_provider.iter_article_recommendation_for_article_dois(
                    (
                        article_mention.article_doi
                        for article_mention in (
                            app_providers_and_models
                            .lists_model.iter_article_mentions_by_list_id(
                               list_id
                            )
                        )
                    ),
                    max_recommendations=max_recommendations
                )
            )
        )
        item_count = len(all_article_recommendations)
        article_recommendation_with_article_meta = list(
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                all_article_recommendations,
                page=page,
                items_per_page=items_per_page
            )
        )
        LOGGER.info(
            'article_recommendation_with_article_meta[:1]=%r',
            article_recommendation_with_article_meta[:1]
        )

        url_pagination_state = get_url_pagination_state_for_url(
            url=request.url,
            page=page,
            items_per_page=items_per_page,
            item_count=item_count,
            enable_pagination=enable_pagination
        )
        rss_url = (
            request
            .url
            .remove_query_params(['page', 'items_per_page', 'enable_pagination'])
            .replace(
                path=request.url.path + '/atom.xml'
            )
        )
        return templates.TemplateResponse(
            'pages/article-recommendations-by-sciety-list-id.html', {
                'request': request,
                'page_title': get_page_title(
                    f'Article recommendations for {list_summary_data.list_meta.list_name}'
                ),
                'rss_url': rss_url,
                'owner_url': get_owner_url(list_summary_data.owner),
                'list_summary_data': list_summary_data,
                'article_list_content': article_recommendation_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    @app.get('/lists/by-id/{list_id}/article-recommendations/atom.xml', response_class=AtomResponse)
    def article_recommendations_atom_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: Optional[int] = DEFAULT_ARTICLE_RECOMMENDATION_RSS_ITEM_COUNT,
        page: int = 1,
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
    ):
        list_summary_data = (
            app_providers_and_models.lists_model.get_list_summary_data_by_list_id(list_id)
        )
        LOGGER.info('list_summary_data: %r', list_summary_data)
        article_recommendation_list = (
            app_providers_and_models
            .semantic_scholar_provider.get_article_recommendation_list_for_article_dois(
                (
                    article_mention.article_doi
                    for article_mention in (
                        app_providers_and_models
                        .lists_model.iter_article_mentions_by_list_id(
                            list_id
                        )
                    )
                ),
                max_recommendations=max_recommendations
            )
        )
        recommendation_timestamp = article_recommendation_list.recommendation_timestamp
        all_article_recommendations = list(
            iter_preprint_article_mention(article_recommendation_list.recommendations)
        )
        article_recommendation_with_article_meta = list(
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                all_article_recommendations,
                page=page,
                items_per_page=items_per_page
            )
        )
        LOGGER.info('recommendation_timestamp: %r', recommendation_timestamp)
        return templates.TemplateResponse(
            'pages/article-recommendations-by-sciety-list-id.atom.xml', {
                'request': request,
                'feed_title': (
                    f'Article recommendations for {list_summary_data.list_meta.list_name}'
                ),
                'recommendation_timestamp': recommendation_timestamp,
                'list_summary_data': list_summary_data,
                'article_list_content': article_recommendation_with_article_meta
            },
            media_type=AtomResponse.media_type
        )

    @app.get('/lists/by-twitter-handle/{twitter_handle}', response_class=HTMLResponse)
    def list_by_twitter_handle(
        request: Request,
        twitter_handle: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        enable_pagination: bool = True
    ):
        assert app_providers_and_models.twitter_user_article_list_provider
        twitter_user = (
            app_providers_and_models
            .twitter_user_article_list_provider.get_twitter_user_by_screen_name(
                twitter_handle
            )
        )
        article_mention_iterable = (
            app_providers_and_models
            .twitter_user_article_list_provider.iter_article_mentions_by_user_id(
                twitter_user.user_id
            )
        )
        article_mention_with_article_meta = list(
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                article_mention_iterable, page=page, items_per_page=items_per_page
            )
        )
        LOGGER.info(
            'article_mention_with_article_meta[:1]=%r', article_mention_with_article_meta[:1]
        )

        # Note: we don't know the page count unless this is the last page
        url_pagination_state = get_url_pagination_state_for_url(
            url=request.url,
            page=page,
            items_per_page=items_per_page,
            remaining_item_iterable=article_mention_iterable,
            enable_pagination=enable_pagination
        )
        return templates.TemplateResponse(
            'pages/list-by-twitter-handle.html', {
                'request': request,
                'page_title': get_page_title(
                    f'Twitter curations by {twitter_user.name} (@{twitter_handle})'
                ),
                'twitter_handle': twitter_handle,
                'twitter_user': twitter_user,
                'article_list_content': article_mention_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    @app.get('/articles/by', response_class=HTMLResponse)
    def article_by_article_doi(
        request: Request,
        article_doi: str
    ):
        try:
            article_meta = (
                app_providers_and_models
                .crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
            )
        except requests.exceptions.HTTPError as exception:
            status_code = exception.response.status_code
            LOGGER.info('Exception retrieving metadata (%r): %r', status_code, exception)
            if status_code != 404:
                raise
            return templates.TemplateResponse(
                'errors/error.html', {
                    'request': request,
                    'page_title': get_page_title(f'Article not found: {article_doi}'),
                    'error_message': f'Article not found: {article_doi}',
                    'exception': exception
                },
                status_code=404
            )
        LOGGER.info('article_meta=%r', article_meta)

        article_stats = (
            app_providers_and_models
            .evaluation_stats_model.get_article_stats_by_article_doi(article_doi)
        )
        article_images = (
            app_providers_and_models
            .google_sheet_article_image_provider.get_article_images_by_doi(article_doi)
        )

        try:
            all_article_recommendations = list(
                iter_preprint_article_mention(
                    app_providers_and_models
                    .semantic_scholar_provider.iter_article_recommendation_for_article_dois(
                        [article_doi],
                        max_recommendations=DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
                    )
                )
            )
        except requests.exceptions.HTTPError as exc:
            LOGGER.warning('failed to get recommendations for %r due to %r', article_doi, exc)
            all_article_recommendations = []
        article_recommendation_with_article_meta = list(
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                all_article_recommendations,
                page=1,
                items_per_page=3
            )
        )
        LOGGER.info(
            'article_recommendation_with_article_meta[:1]=%r',
            article_recommendation_with_article_meta[:1]
        )

        article_recommendation_url = (
            request.url.replace(path='/articles/article-recommendations/by')
        )

        return templates.TemplateResponse(
            'pages/article-by-article-doi.html', {
                'request': request,
                'page_title': get_page_title(article_meta.article_title),
                'page_description': remove_markup_or_none(
                    article_meta.abstract
                ),
                'article_meta': article_meta,
                'article_stats': article_stats,
                'article_images': article_images,
                'article_recommendation_list': article_recommendation_with_article_meta,
                'article_recommendation_url': article_recommendation_url
            }
        )

    @app.get('/articles/article-recommendations/by', response_class=HTMLResponse)
    def article_recommendations_by_article_doi(  # pylint: disable=too-many-arguments
        request: Request,
        article_doi: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS,
        enable_pagination: bool = True
    ):
        article_meta = (
            app_providers_and_models
            .crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
        )
        all_article_recommendations = list(
            iter_preprint_article_mention(
                app_providers_and_models
                .semantic_scholar_provider.iter_article_recommendation_for_article_dois(
                    [article_doi],
                    max_recommendations=max_recommendations
                )
            )
        )
        item_count = len(all_article_recommendations)
        article_recommendation_with_article_meta = list(
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                all_article_recommendations,
                page=page,
                items_per_page=items_per_page
            )
        )
        LOGGER.info(
            'article_recommendation_with_article_meta[:1]=%r',
            article_recommendation_with_article_meta[:1]
        )

        url_pagination_state = get_url_pagination_state_for_url(
            url=request.url,
            page=page,
            items_per_page=items_per_page,
            item_count=item_count,
            enable_pagination=enable_pagination
        )
        return templates.TemplateResponse(
            'pages/article-recommendations-by-article-doi.html', {
                'request': request,
                'page_title': get_page_title(
                    f'Article recommendations for {article_meta.article_title}'
                ),
                'article_meta': article_meta,
                'article_list_content': article_recommendation_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    @app.get('/search', response_class=HTMLResponse)
    def search(  # pylint: disable=too-many-arguments, too-many-locals
        request: Request,
        query: str = '',
        evaluated_only: bool = False,
        search_provider: str = SearchProviders.SEMANTIC_SCHOLAR,
        sort_by: str = SearchSortBy.RELEVANCE,
        date_range: str = SearchDateRange.LAST_90_DAYS,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        enable_pagination: bool = True
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
                _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                    iter_preprint_article_mention(
                        search_result_iterator
                    ),
                    page=page,
                    items_per_page=items_per_page
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
        url_pagination_state = get_url_pagination_state_for_url(
            url=request.url,
            page=page,
            is_this_page_empty=not search_result_list_with_article_meta,
            items_per_page=items_per_page,
            remaining_item_iterable=search_result_iterator,
            enable_pagination=enable_pagination
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

    return app
