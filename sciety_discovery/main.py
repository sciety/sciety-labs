import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from sciety_discovery.models.lists import ScietyEventListsModel
from sciety_discovery.providers.sciety_event import ScietyEventProvider
from sciety_discovery.utils.bq_cache import BigQueryTableModifiedInMemorySingleObjectCache
from sciety_discovery.utils.threading import UpdateThread


LOGGER = logging.getLogger(__name__)


def create_app():
    gcp_project_name = 'elife-data-pipeline'
    sciety_event_table_id = f'{gcp_project_name}.de_proto.sciety_event_v1'
    update_interval_in_secs = 60 * 60  # 1 hour
    min_article_count = 2

    query_results_cache = BigQueryTableModifiedInMemorySingleObjectCache(
        gcp_project_name=gcp_project_name,
        table_id=sciety_event_table_id
    )

    sciety_event_provider = ScietyEventProvider(
        gcp_project_name=gcp_project_name,
        query_results_cache=query_results_cache
    )

    lists_model = ScietyEventListsModel(
        sciety_event_provider.get_sciety_event_dict_list()
    )

    UpdateThread(
        update_interval_in_secs=update_interval_in_secs,
        update_fn=lambda: lists_model.apply_events(
            sciety_event_provider.get_sciety_event_dict_list()
        )
    ).start()

    templates = Jinja2Templates(directory="templates")

    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static", html=False), name="static")

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
        return templates.TemplateResponse(
            "list-by-twitter-handle.html", {
                "request": request,
                "twitter_handle": twitter_handle,
                "article_list_content": [{
                    "article_doi": "10.1101/2022.07.06.22277306",
                    "article_title": "10.1101/2022.07.06.22277306",
                }]
            }
        )

    return app
