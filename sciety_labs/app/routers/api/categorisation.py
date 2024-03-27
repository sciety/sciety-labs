import logging

import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request


LOGGER = logging.getLogger(__name__)


def create_api_categorisation_router(
    app_providers_and_models: AppProvidersAndModels
) -> fastapi.APIRouter:
    router = fastapi.APIRouter()

    @router.get(
        '/categorisation/v1/categories/by/doi'
    )
    async def categories_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        doc = await (
            app_providers_and_models
            .async_opensearch_client
            .get_source(
                index=app_providers_and_models.opensearch_config.index_name,
                id=article_doi,
                _source_includes=['crossref.group_title'],
                headers=get_cache_control_headers_for_request(request)
            )
        )
        return doc
    return router
