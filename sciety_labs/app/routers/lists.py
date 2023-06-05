import logging
from typing import Callable

import starlette.status

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels


LOGGER = logging.getLogger(__name__)


def create_lists_router(
    app_providers_and_models: AppProvidersAndModels,
    min_article_count: int,
    templates: Jinja2Templates,
    get_page_title: Callable[[str], str]
):
    router = APIRouter()

    def _render_lists(request: Request, page_title: str):
        user_list_summary_data_list = list(
            app_providers_and_models
            .google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                app_providers_and_models.lists_model.get_most_active_user_lists(
                    min_article_count=min_article_count
                )
            )
        )
        LOGGER.info('user_list_summary_data_list[:1]=%r', user_list_summary_data_list[:1])
        group_list_summary_data_list = list(
            app_providers_and_models
            .google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                app_providers_and_models.lists_model.get_most_active_group_lists(
                    min_article_count=min_article_count
                )
            )
        )
        LOGGER.info('group_list_summary_data_list[:1]=%r', group_list_summary_data_list[:1])
        return templates.TemplateResponse(
            'pages/lists.html', {
                'request': request,
                'page_title': page_title,
                'user_lists': user_list_summary_data_list,
                'group_lists': group_list_summary_data_list
            }
        )

    @router.get('/lists/user-lists', response_class=HTMLResponse)
    def user_lists(request: Request):
        return _render_lists(request, page_title=get_page_title('Most active user lists'))

    @router.get('/lists/group-lists', response_class=HTMLResponse)
    def group_lists(request: Request):
        return _render_lists(request, page_title=get_page_title('Most active group lists'))

    @router.get('/lists', response_class=RedirectResponse)
    def lists():
        return RedirectResponse('/lists/user-lists', status_code=starlette.status.HTTP_302_FOUND)

    return router
