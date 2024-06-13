import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


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

    return router
