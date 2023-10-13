import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.app_update_manager import AppUpdateManager

from sciety_labs.app.routers.api.api_maintenance import create_api_maintenance_router
from sciety_labs.app.routers.api.article_recommendation import (
    create_api_article_recommendation_router
)


def create_api_app(
    app_providers_and_models: AppProvidersAndModels,
    app_update_manager: AppUpdateManager
) -> fastapi.FastAPI:
    app = fastapi.FastAPI(title='Sciety Labs API', version='1.0.0')

    app.include_router(create_api_maintenance_router(
        app_update_manager=app_update_manager
    ))
    app.include_router(create_api_article_recommendation_router(
        app_providers_and_models=app_providers_and_models
    ))
    return app
