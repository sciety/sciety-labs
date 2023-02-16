from datetime import timedelta
from http.client import HTTPException
from itertools import islice
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import requests_cache
from sciety_discovery.models.evaluation import ScietyEventEvaluationStatsModel

from sciety_discovery.models.lists import ScietyEventListsModel
from sciety_discovery.providers.crossref import (
    CrossrefMetaDataProvider
)
from sciety_discovery.providers.sciety_event import ScietyEventProvider
from sciety_discovery.providers.twitter import get_twitter_user_article_list_provider_or_none
from sciety_discovery.utils.bq_cache import BigQueryTableModifiedInMemorySingleObjectCache
from sciety_discovery.utils.cache import ChainedObjectCache, DiskSingleObjectCache
from sciety_discovery.utils.pagination import (
    UrlPaginationState,
    get_page_count_for_item_count_and_items_per_page
)
from sciety_discovery.utils.threading import UpdateThread


LOGGER = logging.getLogger(__name__)


def create_app():  # pylint: disable=too-many-locals, too-many-statements
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
        match_headers=False
    )

    sciety_event_provider = ScietyEventProvider(
        gcp_project_name=gcp_project_name,
        query_results_cache=query_results_cache
    )

    _sciety_event_dict_list = sciety_event_provider.get_sciety_event_dict_list()
    lists_model = ScietyEventListsModel(_sciety_event_dict_list)
    evaluation_stats_model = ScietyEventEvaluationStatsModel(_sciety_event_dict_list)

    twitter_user_article_list_provider = get_twitter_user_article_list_provider_or_none(
        requests_session=cached_requests_session
    )

    crossref_metadata_provider = CrossrefMetaDataProvider(
        requests_session=cached_requests_session
    )

    UpdateThread(
        update_interval_in_secs=update_interval_in_secs,
        update_fn=lambda: lists_model.apply_events(
            sciety_event_provider.get_sciety_event_dict_list()
        )
    ).start()

    templates = Jinja2Templates(directory='templates')

    app = FastAPI()
    app.mount('/static', StaticFiles(directory='static', html=False), name='static')

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            'errors/404.html', {'request': request, 'exception': exception},
            status_code=404
        )

    @app.exception_handler(500)
    async def server_error_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            'errors/500.html', {'request': request, 'exception': exception},
            status_code=500
        )

    @app.get('/', response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            'index.html', {
                'request': request,
                'user_lists': lists_model.get_most_active_user_lists(
                    top_n=3,
                    min_article_count=min_article_count
                )
            }
        )

    @app.get('/lists', response_class=HTMLResponse)
    async def lists(request: Request):
        return templates.TemplateResponse(
            'lists.html', {
                'request': request,
                'user_lists': lists_model.get_most_active_user_lists(
                    min_article_count=min_article_count
                )
            }
        )

    @app.get('/lists/by-id/{list_id}', response_class=HTMLResponse)
    async def lists_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: int = 10,
        page: int = 1,
        enable_pagination: bool = True
    ):
        list_summary_data = lists_model.get_list_summary_data_by_list_id(list_id)
        item_count = list_summary_data.article_count
        article_mention_iterable = (
            lists_model.iter_article_mentions_by_list_id(list_id)
        )
        article_mention_iterable = (
            evaluation_stats_model.iter_article_mention_with_article_stats(
                article_mention_iterable
            )
        )
        if items_per_page:
            assert page >= 1
            paged_article_mention_iterable = islice(
                article_mention_iterable,
                (page - 1) * items_per_page,  # start
                page * items_per_page  # stop
            )
        else:
            paged_article_mention_iterable = article_mention_iterable
        article_mention_with_article_meta = list(
            crossref_metadata_provider.iter_article_mention_with_article_meta(
                paged_article_mention_iterable
            )
        )
        LOGGER.info('article_mention_with_article_meta: %r', article_mention_with_article_meta)

        page_count: Optional[int] = None
        previous_page_url: Optional[str] = None
        next_page_url: Optional[str] = None
        if enable_pagination:
            page_count = get_page_count_for_item_count_and_items_per_page(
                item_count=item_count, items_per_page=items_per_page
            )
            if page > 1:
                previous_page_url = str(request.url.include_query_params(
                    page=page - 1
                ))
            if page < page_count:
                next_page_url = str(request.url.include_query_params(
                    page=page + 1
                ))
                LOGGER.info('next_page_url: %r', next_page_url)
            else:
                LOGGER.info('no more items past this page')
                page_count = page

        return templates.TemplateResponse(
            'list-by-sciety-list-id.html', {
                'request': request,
                'list_summary_data': list_summary_data,
                'article_list_content': article_mention_with_article_meta,
                'pagination': UrlPaginationState(
                    page=page,
                    page_count=page_count,
                    previous_page_url=previous_page_url,
                    next_page_url=next_page_url
                )
            }
        )

    @app.get('/lists/by-twitter-handle/{twitter_handle}', response_class=HTMLResponse)
    async def list_by_twitter_handle(
        request: Request,
        twitter_handle: str,
        items_per_page: int = 10,
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
        article_mention_iterable = (
            evaluation_stats_model.iter_article_mention_with_article_stats(
                article_mention_iterable
            )
        )
        if items_per_page:
            assert page >= 1
            paged_article_mention_iterable = islice(
                article_mention_iterable,
                (page - 1) * items_per_page,  # start
                page * items_per_page  # stop
            )
        else:
            paged_article_mention_iterable = article_mention_iterable
        article_mention_with_article_meta = list(
            crossref_metadata_provider.iter_article_mention_with_article_meta(
                paged_article_mention_iterable
            )
        )
        LOGGER.info('article_mention_with_article_meta: %r', article_mention_with_article_meta)

        # we don't know the page count unless this is the last page
        page_count: Optional[int] = None
        previous_page_url: Optional[str] = None
        next_page_url: Optional[str] = None
        if enable_pagination:
            if page > 1:
                previous_page_url = str(request.url.include_query_params(
                    page=page - 1
                ))
            if next(article_mention_iterable, None) is not None:
                next_page_url = str(request.url.include_query_params(
                    page=page + 1
                ))
                LOGGER.info('next_page_url: %r', next_page_url)
            else:
                LOGGER.info('no more items past this page')
                page_count = page

        return templates.TemplateResponse(
            'list-by-twitter-handle.html', {
                'request': request,
                'twitter_handle': twitter_handle,
                'twitter_user': twitter_user,
                'article_list_content': article_mention_with_article_meta,
                'pagination': UrlPaginationState(
                    page=page,
                    page_count=page_count,
                    previous_page_url=previous_page_url,
                    next_page_url=next_page_url
                )
            }
        )

    return app
