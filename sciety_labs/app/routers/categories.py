import logging

from fastapi import APIRouter, Request
import fastapi
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import AnnotatedPaginationParameters, get_page_title
from sciety_labs.providers.papers.async_papers import PageNumberBasedPaginationParameters
from sciety_labs.utils.pagination import get_url_pagination_state_for_pagination_parameters


LOGGER = logging.getLogger(__name__)


def create_categories_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    article_aggregator = app_providers_and_models.article_aggregator

    router = APIRouter()

    @router.get('/categories', response_class=HTMLResponse)
    async def categories(
        request: Request,
        evaluated_only: bool = True
    ):
        category_display_names = await (
            app_providers_and_models
            .async_paper_provider
            .get_category_display_name_list(
                evaluated_only=evaluated_only
            )
        )
        return templates.TemplateResponse(
            request=request,
            name='pages/categories-list.html',
            context={
                'page_title': 'Browse Categories',
                'category_display_names': category_display_names
            }
        )

    @router.get('/categories/articles', response_class=HTMLResponse)
    async def list_by_sciety_list_id(
        request: Request,
        category: str,
        pagination_parameters: AnnotatedPaginationParameters,
        from_sciety: bool = False,
        from_sciety_alias: bool = fastapi.Query(False, alias='from-sciety'),
        evaluated_only: bool = True
    ):
        search_results_list = await (
            app_providers_and_models
            .async_paper_provider
            .get_preprints_for_category_search_results_list(
                category=category,
                evaluated_only=evaluated_only,
                pagination_parameters=PageNumberBasedPaginationParameters(
                    page=pagination_parameters.page,
                    items_per_page=pagination_parameters.items_per_page
                )
            )
        )
        article_mention_with_article_meta = (
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                search_results_list.items,
                page=1,  # pagination is handled by service
                items_per_page=pagination_parameters.items_per_page
            )
        )
        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url,
            pagination_parameters=pagination_parameters,
            item_count=search_results_list.total
        )
        return templates.TemplateResponse(
            request=request,
            name='pages/categories-articles.html',
            context={
                'page_title': get_page_title(
                    category
                ),
                'category_display_name': category,
                'from_sciety': from_sciety or from_sciety_alias,
                'article_list_content': article_mention_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    return router
