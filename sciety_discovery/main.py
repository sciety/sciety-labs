import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from sciety_discovery.models.lists import ScietyEventListsModel
from sciety_discovery.providers.sciety_event import ScietyEventProvider
from sciety_discovery.utils.bq_cache import BigQueryTableModifiedInMemorySingleObjectCache


LOGGER = logging.getLogger(__name__)


def create_app():
    gcp_project_name = 'elife-data-pipeline'
    sciety_event_table_id = f'{gcp_project_name}.de_proto.sciety_event_v1'

    query_results_cache = BigQueryTableModifiedInMemorySingleObjectCache(
        gcp_project_name=gcp_project_name,
        table_id=sciety_event_table_id
    )

    sciety_event_provider = ScietyEventProvider(
        gcp_project_name=gcp_project_name,
        query_results_cache=query_results_cache
    )

    templates = Jinja2Templates(directory="templates")

    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static", html=False), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        lists_model = ScietyEventListsModel(
            sciety_event_provider.get_sciety_event_dict_list()
        )
        return templates.TemplateResponse(
            "index.html", {
                "request": request,
                "user_lists": lists_model.get_most_active_user_lists()
            }
        )

    return app
