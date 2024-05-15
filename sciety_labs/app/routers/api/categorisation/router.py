import logging
from typing import Mapping, Optional

import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request


LOGGER = logging.getLogger(__name__)


class AsyncOpenSearchCategoriesProvider:
    def __init__(self, app_providers_and_models: AppProvidersAndModels):
        self.async_opensearch_client = app_providers_and_models.async_opensearch_client
        self.index_name = app_providers_and_models.opensearch_config.index_name

    async def get_categories_dict_by_doi(
        self,
        article_doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> dict:
        doc = await (
            self.async_opensearch_client.get_source(
                index=self.index_name,
                id=article_doi,
                _source_includes=['crossref.group_title'],
                headers=headers
            )
        )
        return doc


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
        return async_opensearch_categories_provider.get_categories_dict_by_doi(
            article_doi=article_doi,
            headers=get_cache_control_headers_for_request(request)
        )
    return router
