import logging
from typing import Mapping, Optional

import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request


LOGGER = logging.getLogger(__name__)


async def get_categories_dict_by_doi(
    article_doi: str,
    app_providers_and_models: AppProvidersAndModels,
    headers: Optional[Mapping[str, str]] = None
) -> dict:
    doc = await (
        app_providers_and_models
        .async_opensearch_client
        .get_source(
            index=app_providers_and_models.opensearch_config.index_name,
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

    @router.get(
        '/categorisation/v1/categories/by/doi'
    )
    async def categories_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        return get_categories_dict_by_doi(
            article_doi=article_doi,
            app_providers_and_models=app_providers_and_models,
            headers=get_cache_control_headers_for_request(request)
        )
    return router
