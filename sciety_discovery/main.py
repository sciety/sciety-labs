from datetime import timedelta
from http.client import HTTPException
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import requests_cache

from sciety_discovery.models.lists import ScietyEventListsModel
from sciety_discovery.providers.crossref import (
    CrossrefMetaDataProvider
)
from sciety_discovery.providers.sciety_event import ScietyEventProvider
from sciety_discovery.providers.twitter import get_twitter_user_article_list_provider_or_none
from sciety_discovery.utils.bq_cache import BigQueryTableModifiedInMemorySingleObjectCache
from sciety_discovery.utils.cache import ChainedObjectCache, DiskSingleObjectCache
from sciety_discovery.utils.threading import UpdateThread


LOGGER = logging.getLogger(__name__)


def create_app():  # pylint: disable=too-many-locals
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

    lists_model = ScietyEventListsModel(
        sciety_event_provider.get_sciety_event_dict_list()
    )

    twitter_user_article_list_provider = get_twitter_user_article_list_provider_or_none(
        requests_session=cached_requests_session
    )

    crossref_metadata_provider = CrossrefMetaDataProvider()

    UpdateThread(
        update_interval_in_secs=update_interval_in_secs,
        update_fn=lambda: lists_model.apply_events(
            sciety_event_provider.get_sciety_event_dict_list()
        )
    ).start()

    templates = Jinja2Templates(directory="templates")

    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static", html=False), name="static")

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            "errors/404.html", {"request": request, "exception": exception},
            status_code=404
        )

    @app.exception_handler(500)
    async def server_error_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            "errors/500.html", {"request": request, "exception": exception},
            status_code=500
        )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            "index.html", {
                "request": request,
                "user_lists": lists_model.get_most_active_user_lists(
                    top_n=3,
                    min_article_count=min_article_count
                )
            }
        )

    @app.get("/lists", response_class=HTMLResponse)
    async def lists(request: Request):
        return templates.TemplateResponse(
            "lists.html", {
                "request": request,
                "user_lists": lists_model.get_most_active_user_lists(
                    min_article_count=min_article_count
                )
            }
        )

    @app.get("/lists/by-twitter-handle/{twitter_handle}", response_class=HTMLResponse)
    async def list_by_twitter_handle(request: Request, twitter_handle: str):
        assert twitter_user_article_list_provider
        article_mention_iterable = (
            twitter_user_article_list_provider.iter_article_mentions_by_screen_name(
                twitter_handle
            )
        )
        article_mention_with_article_meta = list(
            crossref_metadata_provider.iter_article_mention_with_article_meta(
                article_mention_iterable
            )
        )
        LOGGER.info('article_mention_with_article_meta: %r', article_mention_with_article_meta)

        return templates.TemplateResponse(
            "list-by-twitter-handle.html", {
                "request": request,
                "twitter_handle": twitter_handle,
                "article_list_content": article_mention_with_article_meta
            }
        )

    return app
