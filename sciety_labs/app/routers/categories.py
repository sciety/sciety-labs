import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import AnnotatedPaginationParameters, get_page_title


LOGGER = logging.getLogger(__name__)


def create_categories_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    article_aggregator = app_providers_and_models.article_aggregator

    router = APIRouter()

    @router.get('/categories', response_class=HTMLResponse)
    async def categories(
        request: Request
    ):
        return templates.TemplateResponse(
            request=request,
            name='pages/categories-list.html',
            context={
                'page_title': 'Browse Categories',
                'category_display_names': [
                    'Neuroscience',
                    'Microbiology'
                ]
            }
        )

    @router.get('/categories/articles', response_class=HTMLResponse)
    async def list_by_sciety_list_id(
        request: Request,
        category: str,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        search_results_list = await (
            app_providers_and_models
            .async_paper_provider
            .get_preprints_for_category_search_results_list(
                category=category
            )
        )
        article_mention_with_article_meta = (
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                search_results_list.items,
                page=pagination_parameters.page,
                items_per_page=pagination_parameters.items_per_page
            )
        )
        return templates.TemplateResponse(
            request=request,
            name='pages/category-articles.html',
            context={
                'page_title': get_page_title(
                    category
                ),
                'category_display_name': category,
                'article_list_content': article_mention_with_article_meta
            }
        )

    return router
