from datetime import timedelta
from http.client import HTTPException
import logging
from pathlib import Path
from typing import Iterable, Optional

import requests

import starlette.responses
import starlette.status

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import requests_cache

import markupsafe

import bleach
from sciety_labs.config.site_config import get_site_config_from_environment_variables

from sciety_labs.models.article import ArticleMention, iter_preprint_article_mention
from sciety_labs.models.evaluation import ScietyEventEvaluationStatsModel

from sciety_labs.models.lists import OwnerMetaData, OwnerTypes, ScietyEventListsModel
from sciety_labs.providers.crossref import (
    CrossrefMetaDataProvider
)
from sciety_labs.providers.google_sheet_image import (
    GoogleSheetArticleImageProvider,
    GoogleSheetListImageProvider
)
from sciety_labs.providers.sciety_event import ScietyEventProvider
from sciety_labs.providers.semantic_scholar import (
    DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS,
    SemanticScholarProvider
)
from sciety_labs.providers.twitter import get_twitter_user_article_list_provider_or_none
from sciety_labs.utils.bq_cache import BigQueryTableModifiedInMemorySingleObjectCache
from sciety_labs.utils.cache import (
    ChainedObjectCache,
    DiskSingleObjectCache,
    InMemorySingleObjectCache
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
from sciety_labs.utils.text import remove_markup, remove_markup_or_none
from sciety_labs.utils.threading import UpdateThread


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


class AtomResponse(starlette.responses.Response):
    media_type = "application/atom+xml;charset=utf-8"


def get_owner_url(owner: OwnerMetaData) -> Optional[str]:
    if owner.owner_type == OwnerTypes.USER and owner.twitter_handle:
        return f'https://sciety.org/users/{owner.twitter_handle}'
    if owner.owner_type == OwnerTypes.GROUP and owner.slug:
        return f'https://sciety.org/groups/{owner.slug}'
    return None


def get_sanitized_string_as_safe_markup(text: str) -> markupsafe.Markup:
    return markupsafe.Markup(bleach.clean(text, tags=ALLOWED_TAGS))


def get_page_title(text: str) -> str:
    return remove_markup(text)


def create_app():  # pylint: disable=too-many-locals, too-many-statements
    site_config = get_site_config_from_environment_variables()
    LOGGER.info('site_config: %r', site_config)

    gcp_project_name = 'elife-data-pipeline'
    sciety_event_table_id = f'{gcp_project_name}.de_proto.sciety_event_v1'
    update_interval_in_secs = 60 * 60  # 1 hour
    max_age_in_seconds = 60 * 60  # 1 hour
    min_article_count = 2

    cache_dir = Path('.cache')
    cache_dir.mkdir(parents=True, exist_ok=True)

    query_results_cache = ChainedObjectCache([
        BigQueryTableModifiedInMemorySingleObjectCache(
            gcp_project_name=gcp_project_name,
            table_id=sciety_event_table_id
        ),
        DiskSingleObjectCache(
            file_path=cache_dir / 'query_results_cache.pickle',
            max_age_in_seconds=max_age_in_seconds
        )
    ])

    cached_requests_session = requests_cache.CachedSession(
        '.cache/requests_cache',
        xpire_after=timedelta(days=1),
        allowable_methods=('GET', 'HEAD', 'POST'),  # include POST for Semantic Scholar
        match_headers=False
    )

    sciety_event_provider = ScietyEventProvider(
        gcp_project_name=gcp_project_name,
        query_results_cache=query_results_cache
    )

    lists_model = ScietyEventListsModel([])
    evaluation_stats_model = ScietyEventEvaluationStatsModel([])

    twitter_user_article_list_provider = get_twitter_user_article_list_provider_or_none(
        requests_session=cached_requests_session
    )

    crossref_metadata_provider = CrossrefMetaDataProvider(
        requests_session=cached_requests_session
    )

    semantic_scholar_provider = SemanticScholarProvider(
        requests_session=cached_requests_session
    )

    article_image_mapping_cache = ChainedObjectCache([
        InMemorySingleObjectCache(
            max_age_in_seconds=max_age_in_seconds
        ),
        DiskSingleObjectCache(
            file_path=cache_dir / 'article_image_mapping_cache.pickle',
            max_age_in_seconds=max_age_in_seconds
        )
    ])

    google_sheet_article_image_provider = GoogleSheetArticleImageProvider(
        image_mapping_cache=article_image_mapping_cache,
        refresh_manually=True
    )

    list_image_mapping_cache = ChainedObjectCache([
        InMemorySingleObjectCache(
            max_age_in_seconds=max_age_in_seconds
        ),
        DiskSingleObjectCache(
            file_path=cache_dir / 'list_image_mapping_cache.pickle',
            max_age_in_seconds=max_age_in_seconds
        )
    ])

    google_sheet_list_image_provider = GoogleSheetListImageProvider(
        image_mapping_cache=list_image_mapping_cache,
        refresh_manually=True
    )

    def check_or_reload_data():
        # Note: this may still use a cache
        _sciety_event_dict_list = sciety_event_provider.get_sciety_event_dict_list()
        lists_model.apply_events(_sciety_event_dict_list)
        evaluation_stats_model.apply_events(_sciety_event_dict_list)
        google_sheet_article_image_provider.refresh()
        google_sheet_list_image_provider.refresh()

    UpdateThread(
        update_interval_in_secs=update_interval_in_secs,
        update_fn=check_or_reload_data
    ).start()

    LOGGER.info('Preloading data')
    check_or_reload_data()

    templates = Jinja2Templates(directory='templates')
    templates.env.filters['sanitize'] = get_sanitized_string_as_safe_markup
    templates.env.filters['date_isoformat'] = get_date_as_isoformat
    templates.env.filters['date_display_format'] = get_date_as_display_format
    templates.env.filters['timestamp_isoformat'] = get_timestamp_as_isoformat
    templates.env.globals['site_config'] = site_config

    app = FastAPI()
    app.mount('/static', StaticFiles(directory='static', html=False), name='static')

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
    async def index(request: Request):
        user_list_summary_data_list = list(
            google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                lists_model.get_most_active_user_lists(
                    top_n=3,
                    min_article_count=min_article_count
                )
            )
        )
        LOGGER.info('user_list_summary_data_list: %r', user_list_summary_data_list)
        group_list_summary_data_list = list(
            google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                lists_model.get_most_active_group_lists(
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

    def _render_lists(request: Request, page_title: str):
        user_list_summary_data_list = list(
            google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                lists_model.get_most_active_user_lists(
                    min_article_count=min_article_count
                )
            )
        )
        LOGGER.info('user_list_summary_data_list: %r', user_list_summary_data_list)
        group_list_summary_data_list = list(
            google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                lists_model.get_most_active_group_lists(
                    min_article_count=min_article_count
                )
            )
        )
        LOGGER.info('group_list_summary_data_list: %r', group_list_summary_data_list)
        return templates.TemplateResponse(
            'pages/lists.html', {
                'request': request,
                'page_title': page_title,
                'user_lists': user_list_summary_data_list,
                'group_lists': group_list_summary_data_list
            }
        )

    @app.get('/lists/user-lists', response_class=HTMLResponse)
    async def user_lists(request: Request):
        return _render_lists(request, page_title=get_page_title('Most active user lists'))

    @app.get('/lists/group-lists', response_class=HTMLResponse)
    async def group_lists(request: Request):
        return _render_lists(request, page_title=get_page_title('Most active group lists'))

    @app.get('/lists', response_class=RedirectResponse)
    async def lists():
        return RedirectResponse('/lists/user-lists', status_code=starlette.status.HTTP_302_FOUND)

    def _get_page_article_mention_with_article_meta_for_article_mention_iterable(
        article_mention_iterable: Iterable[ArticleMention],
        page: int,
        items_per_page: Optional[int]
    ) -> Iterable[ArticleMention]:
        article_mention_iterable = (
            evaluation_stats_model.iter_article_mention_with_article_stats(
                article_mention_iterable
            )
        )
        article_mention_with_article_meta = (
            crossref_metadata_provider.iter_article_mention_with_article_meta(
                get_page_iterable(
                    article_mention_iterable, page=page, items_per_page=items_per_page
                )
            )
        )
        article_mention_with_article_meta = (
            google_sheet_article_image_provider.iter_article_mention_with_article_image_url(
                article_mention_with_article_meta
            )
        )
        article_mention_with_article_meta = list(article_mention_with_article_meta)
        LOGGER.info('article_mention_with_article_meta: %r', article_mention_with_article_meta)
        return article_mention_with_article_meta

    @app.get('/lists/by-id/{list_id}', response_class=HTMLResponse)
    async def list_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        enable_pagination: bool = True
    ):
        list_summary_data = lists_model.get_list_summary_data_by_list_id(list_id)
        LOGGER.info('list_summary_data: %r', list_summary_data)
        list_images = google_sheet_list_image_provider.get_list_images_by_list_id(list_id)
        LOGGER.info('list_images: %r', list_images)
        item_count = list_summary_data.article_count
        article_mention_with_article_meta = (
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                lists_model.iter_article_mentions_by_list_id(list_id),
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
    async def list_atom_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: Optional[int] = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1
    ):
        list_summary_data = lists_model.get_list_summary_data_by_list_id(list_id)
        LOGGER.info('list_summary_data: %r', list_summary_data)
        article_mention_with_article_meta = (
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                lists_model.iter_article_mentions_by_list_id(list_id),
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
    async def article_recommendations_by_sciety_list_id(  # pylint: disable=too-many-arguments
        request: Request,
        list_id: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS,
        enable_pagination: bool = True
    ):
        list_summary_data = lists_model.get_list_summary_data_by_list_id(list_id)
        all_article_recommendations = list(
            iter_preprint_article_mention(
                semantic_scholar_provider.iter_article_recommendation_for_article_dois(
                    (
                        article_mention.article_doi
                        for article_mention in lists_model.iter_article_mentions_by_list_id(
                            list_id
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
            'article_recommendation_with_article_meta=%r',
            article_recommendation_with_article_meta
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
    async def article_recommendations_atom_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: Optional[int] = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
    ):
        list_summary_data = lists_model.get_list_summary_data_by_list_id(list_id)
        LOGGER.info('list_summary_data: %r', list_summary_data)
        article_recommendation_list = (
            semantic_scholar_provider.get_article_recommendation_list_for_article_dois(
                (
                    article_mention.article_doi
                    for article_mention in lists_model.iter_article_mentions_by_list_id(
                        list_id
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
    async def list_by_twitter_handle(
        request: Request,
        twitter_handle: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        enable_pagination: bool = True
    ):
        assert twitter_user_article_list_provider
        twitter_user = twitter_user_article_list_provider.get_twitter_user_by_screen_name(
            twitter_handle
        )
        article_mention_iterable = (
            twitter_user_article_list_provider.iter_article_mentions_by_user_id(
                twitter_user.user_id
            )
        )
        article_mention_with_article_meta = list(
            _get_page_article_mention_with_article_meta_for_article_mention_iterable(
                article_mention_iterable, page=page, items_per_page=items_per_page
            )
        )
        LOGGER.info('article_mention_with_article_meta: %r', article_mention_with_article_meta)

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
    async def article_by_article_doi(
        request: Request,
        article_doi: str
    ):
        try:
            article_meta = crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
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

        article_images = google_sheet_article_image_provider.get_article_images_by_doi(article_doi)

        try:
            all_article_recommendations = list(
                iter_preprint_article_mention(
                    semantic_scholar_provider.iter_article_recommendation_for_article_dois(
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
            'article_recommendation_with_article_meta=%r',
            article_recommendation_with_article_meta
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
                'article_images': article_images,
                'article_recommendation_list': article_recommendation_with_article_meta,
                'article_recommendation_url': article_recommendation_url
            }
        )

    @app.get('/articles/article-recommendations/by', response_class=HTMLResponse)
    async def article_recommendations_by_article_doi(  # pylint: disable=too-many-arguments
        request: Request,
        article_doi: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS,
        enable_pagination: bool = True
    ):
        article_meta = crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
        all_article_recommendations = list(
            iter_preprint_article_mention(
                semantic_scholar_provider.iter_article_recommendation_for_article_dois(
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
            'article_recommendation_with_article_meta=%r',
            article_recommendation_with_article_meta
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

    return app
