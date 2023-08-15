import logging
from typing import Iterable, Set

import starlette.status

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.list_by_id import create_list_by_id_router
from sciety_labs.app.routers.list_by_twitter_handle import create_list_by_twitter_handle_router
from sciety_labs.app.utils.common import (
    get_page_title
)
from sciety_labs.models.lists import ListSummaryData


LOGGER = logging.getLogger(__name__)

# exclude some lists of users who's avatar no longer resolves
HIDDEN_LIST_IDS = {
    'c145fb46-9487-4910-ae25-aa3e9f3fa5e8',
    'b8b1abc5-9b8e-42b7-bc10-e01572d1d5d4',
    '8f612ad9-fb88-461a-ab38-4b7f681e8ffe',
    '36c8bff1-f5f2-4c8a-b2b2-190af01ad9e6',
    'e89549c2-6dc6-4d31-a72f-e6b90a496458',
    '7223b4bf-2163-4f45-9457-7bd9524cf779',
    'a9bf8053-032d-421e-ab5c-4a9cb88b91b4',
    '78fc6d8c-8bca-49e8-86cc-8a676688d476',
    'c8ccd202-b62f-4c92-897c-3c1fb6275401',
    '55b5810b-d255-46d1-8372-7cf4f16595b9',
    '0e634779-68fa-4209-87f7-8cb5046a3c94'
}


def iter_list_summary_data_not_matching_list_ids(
    list_summary_data_iterable: Iterable[ListSummaryData],
    exclude_list_ids: Set[str]
) -> Iterable[ListSummaryData]:
    return (
        list_summary_data
        for list_summary_data in list_summary_data_iterable
        if list_summary_data.list_meta.list_id not in exclude_list_ids
    )


def create_lists_router(
    app_providers_and_models: AppProvidersAndModels,
    min_article_count: int,
    templates: Jinja2Templates
):
    router = APIRouter()
    router.include_router(create_list_by_id_router(
        app_providers_and_models=app_providers_and_models,
        templates=templates
    ))
    router.include_router(create_list_by_twitter_handle_router(
        app_providers_and_models=app_providers_and_models,
        templates=templates
    ))

    def _render_lists(request: Request, page_title: str):
        user_list_summary_data_list = list(
            app_providers_and_models
            .google_sheet_list_image_provider.iter_list_summary_data_with_list_image_url(
                iter_list_summary_data_not_matching_list_ids(
                    app_providers_and_models.lists_model.get_most_active_user_lists(
                        min_article_count=min_article_count
                    ),
                    HIDDEN_LIST_IDS
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
