from http.client import HTTPException
import logging

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import markupsafe

import bleach
from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.app_update_manager import AppUpdateManager
from sciety_labs.app.routers.api.api_maintenance import create_api_maintenance_router
from sciety_labs.app.routers.api.article_recommendation import (
    create_api_article_recommendation_router
)
from sciety_labs.app.routers.articles import create_articles_router
from sciety_labs.app.routers.home import create_home_router
from sciety_labs.app.routers.lists import create_lists_router
from sciety_labs.app.routers.search import create_search_router
from sciety_labs.app.utils.common import (
    get_page_title
)
from sciety_labs.config.search_feed_config import load_search_feeds_config
from sciety_labs.config.site_config import get_site_config_from_environment_variables

from sciety_labs.utils.datetime import (
    get_date_as_display_format,
    get_date_as_isoformat,
    get_timestamp_as_isoformat
)


LOGGER = logging.getLogger(__name__)


ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'bold',
    'code',
    'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
    'h1', 'h2', 'h3', 'p', 'img', 'video', 'div',
    'p', 'br', 'span', 'hr', 'src', 'class',
    'section', 'sub', 'sup'
]


def get_sanitized_string_as_safe_markup(text: str) -> markupsafe.Markup:
    return markupsafe.Markup(bleach.clean(text, tags=ALLOWED_TAGS))


def create_app():  # pylint: disable=too-many-locals, too-many-statements
    site_config = get_site_config_from_environment_variables()
    LOGGER.info('site_config: %r', site_config)

    search_feeds_config = load_search_feeds_config('config/search-feeds.yaml')
    LOGGER.info('search_feeds_config: %r', search_feeds_config)

    update_interval_in_secs = 60 * 60  # 1 hour
    min_article_count = 2

    app_providers_and_models = AppProvidersAndModels()

    app_update_manager = AppUpdateManager(
        app_providers_and_models=app_providers_and_models
    )
    app_update_manager.start(update_interval_in_secs=update_interval_in_secs)

    LOGGER.info('Preloading data')
    app_update_manager.check_or_reload_data(preload_only=True)

    templates = Jinja2Templates(directory='templates')
    templates.env.filters['sanitize'] = get_sanitized_string_as_safe_markup
    templates.env.filters['date_isoformat'] = get_date_as_isoformat
    templates.env.filters['date_display_format'] = get_date_as_display_format
    templates.env.filters['timestamp_isoformat'] = get_timestamp_as_isoformat
    templates.env.globals['site_config'] = site_config

    app = FastAPI()
    app.mount('/static', StaticFiles(directory='static', html=False), name='static')

    app.include_router(create_api_maintenance_router(
        app_update_manager=app_update_manager
    ))
    app.include_router(create_api_article_recommendation_router(
        app_providers_and_models=app_providers_and_models
    ))
    app.include_router(create_home_router(
        app_providers_and_models=app_providers_and_models,
        min_article_count=min_article_count,
        templates=templates,
        search_feeds_config=search_feeds_config
    ))
    app.include_router(create_lists_router(
        app_providers_and_models=app_providers_and_models,
        min_article_count=min_article_count,
        templates=templates
    ))
    app.include_router(create_articles_router(
        app_providers_and_models=app_providers_and_models,
        templates=templates
    ))
    app.include_router(create_search_router(
        app_providers_and_models=app_providers_and_models,
        templates=templates,
        search_feeds_config=search_feeds_config
    ))

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            'errors/404.html', {
                'request': request,
                'page_title': get_page_title('Page not found'),
                'exception': exception
            },
            status_code=404
        )

    @app.exception_handler(500)
    async def server_error_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            'errors/500.html', {
                'request': request,
                'page_title': get_page_title('Something went wrong'),
                'exception': exception
            },
            status_code=500
        )

    return app
