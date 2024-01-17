from http.client import HTTPException
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.app_templates import get_app_templates
from sciety_labs.app.app_update_manager import AppUpdateManager
from sciety_labs.app.routers.api.app import create_api_app
from sciety_labs.app.routers.articles import create_articles_router
from sciety_labs.app.routers.home import create_home_router
from sciety_labs.app.routers.lists import create_lists_router
from sciety_labs.app.routers.search import create_search_router
from sciety_labs.app.utils.common import (
    get_page_title
)
from sciety_labs.config.search_feed_config import load_search_feeds_config
from sciety_labs.config.site_config import get_site_config_from_environment_variables

from sciety_labs.utils.fastapi import (
    update_request_scope_to_original_url_middleware
)
from sciety_labs.utils.logging import ThreadedLogging
from sciety_labs.utils.uvicorn import RedirectDoubleQueryStringMiddleware


LOGGER = logging.getLogger(__name__)


def _create_app():  # pylint: disable=too-many-locals, too-many-statements
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

    templates = get_app_templates(site_config=site_config)

    app = FastAPI(docs_url=None, redoc_url=None)
    app.mount('/static', StaticFiles(directory='static', html=False), name='static')
    app.mount('/api', create_api_app(
        app_providers_and_models=app_providers_and_models,
        app_update_manager=app_update_manager
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

    app.middleware('http')(update_request_scope_to_original_url_middleware)

    app.add_middleware(RedirectDoubleQueryStringMiddleware)

    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            request=request,
            name='errors/404.html',
            context={
                'page_title': get_page_title('Page not found'),
                'exception': exception
            },
            status_code=404
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_exception_handler(request: Request, exception: HTTPException):
        error_message = 'Something doesn\'t seem right, with the parameters.'
        return templates.TemplateResponse(
            request=request,
            name='errors/error.html',
            context={
                'page_title': get_page_title(error_message),
                'error_message': error_message,
                'exception': exception
            },
            status_code=400
        )

    @app.exception_handler(500)
    async def server_error_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            request=request,
            name='errors/500.html',
            context={
                'page_title': get_page_title('Something went wrong'),
                'exception': exception
            },
            status_code=500
        )

    return app


def create_app():
    ThreadedLogging().__enter__()  # pylint: disable=unnecessary-dunder-call
    LOGGER.info('Creating App...')
    return _create_app()
