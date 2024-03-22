import logging

import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request


LOGGER = logging.getLogger(__name__)


def create_api_experimental_router(
    app_providers_and_models: AppProvidersAndModels
) -> fastapi.APIRouter:
    router = fastapi.APIRouter(include_in_schema=False)

    @router.get(
        '/experimental/sync/opensearch/metadata/by/doi'
    )
    async def experimental_sync_opensearch_metadata_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        doc = await (
            app_providers_and_models
            .async_opensearch_client
            .get_source(
                index=app_providers_and_models.opensearch_config.index_name,
                id=article_doi,
                headers=get_cache_control_headers_for_request(request)
            )
        )
        return doc

    @router.get(
        '/experimental/async/opensearch/metadata/by/doi'
    )
    async def experimental_async_opensearch_metadata_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        doc = await (
            app_providers_and_models
            .async_opensearch_client
            .get_source(
                index=app_providers_and_models.opensearch_config.index_name,
                id=article_doi,
                headers=get_cache_control_headers_for_request(request)
            )
        )
        return doc

    @router.get(
        '/experimental/sync/crossref/metadata/by/doi'
    )
    async def experimental_sync_crossref_metadata_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        return await (
            app_providers_and_models
            .crossref_metadata_provider
            .get_crossref_metadata_dict_by_doi(
                article_doi,
                headers=get_cache_control_headers_for_request(request)
            )
        )

    @router.get(
        '/experimental/async/crossref/metadata/by/doi'
    )
    async def experimental_async_crossref_metadata_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        return await (
            app_providers_and_models
            .crossref_metadata_provider
            .get_crossref_metadata_dict_by_doi(
                article_doi,
                headers=get_cache_control_headers_for_request(request)
            )
        )

    @router.get(
        '/experimental/embedding-vector-for-title-abstract'
    )
    async def experimental_embedding_vector_for_title_abstract(
        request: fastapi.Request,
        title: str,
        abstract: str
    ):
        embedding_vector = await (
            app_providers_and_models
            .title_abstract_embedding_vector_provider
            .get_embedding_vector(
                title=title,
                abstract=abstract,
                headers=get_cache_control_headers_for_request(request)
            )
        )
        return embedding_vector

    return router
