import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels


LOGGER = logging.getLogger(__name__)


def create_home_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates,
    min_article_count: int
):
    router = APIRouter()

    @router.get('/', response_class=HTMLResponse)
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

    return router
