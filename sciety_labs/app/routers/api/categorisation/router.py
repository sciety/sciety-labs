import logging

import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.api.categorisation.providers import (
    AsyncOpenSearchCategoriesProvider
)
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request


LOGGER = logging.getLogger(__name__)


def create_api_categorisation_router(
    app_providers_and_models: AppProvidersAndModels
) -> fastapi.APIRouter:
    router = fastapi.APIRouter()
    async_opensearch_categories_provider = AsyncOpenSearchCategoriesProvider(
        app_providers_and_models=app_providers_and_models
    )

    @router.get(
        '/categorisation/v1/categories/by/doi'
    )
    async def categories_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        return await async_opensearch_categories_provider.get_categories_dict_by_doi(
            article_doi=article_doi,
            headers=get_cache_control_headers_for_request(request)
        )
    return router
