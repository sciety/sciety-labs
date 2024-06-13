import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import get_page_title


LOGGER = logging.getLogger(__name__)


def create_categories_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
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
                    'Plant Science'
                ]
            }
        )

    @router.get('/categories/articles', response_class=HTMLResponse)
    async def list_by_sciety_list_id(
        request: Request,
        category: str
    ):
        # article_list_content: Sequence[ArticleMention] = [
        #     ArticleMention(
        #         article_doi='10.12345/doi_1',
        #         article_meta=ArticleMetaData(
        #             article_doi='10.1234/doi_1',
        #             article_title='Title 1'
        #         )
        #     )
        # ]
        search_results_list = await (
            app_providers_and_models
            .async_paper_provider
            .get_preprints_for_category_search_results_list(
                category=category
            )
        )
        article_list_content = search_results_list.items
        return templates.TemplateResponse(
            request=request,
            name='pages/category-articles.html',
            context={
                'page_title': get_page_title(
                    category
                ),
                'category_display_name': category,
                'article_list_content': article_list_content
            }
        )

    return router
