import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.utils.common import get_page_title


LOGGER = logging.getLogger(__name__)


def create_categories_router(
    templates: Jinja2Templates
):
    router = APIRouter()

    @router.get('/categories', response_class=HTMLResponse)
    def categories(
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
    def list_by_sciety_list_id(
        request: Request,
        category: str
    ):
        return templates.TemplateResponse(
            request=request,
            name='pages/category-articles.html',
            context={
                'page_title': get_page_title(
                    category
                ),
                'category_display_name': category
            }
        )

    return router
