import logging

import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.api.categorisation.providers import (
    ArticleDoiNotFoundError,
    AsyncOpenSearchCategoriesProvider,
    get_default_article_search_sort_parameters
)
from sciety_labs.app.routers.api.categorisation.typing import (
    ArticleSearchResponseDict,
    CategorisationResponseDict,
    JsonApiErrorsResponseDict
)
from sciety_labs.providers.opensearch.utils import (
    OpenSearchFilterParameters
)
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request


LOGGER = logging.getLogger(__name__)


CATEGORISATION_BY_DOI_API_EXAMPLE_200_RESPONSE: CategorisationResponseDict = {
    'data': [{
        'display_name': 'Pain Medicine',
        'type': 'category',
        'source_id': 'crossref_group_title'
    }]
}

CATEGORISATION_BY_DOI_API_EXAMPLE_404_RESPONSE: JsonApiErrorsResponseDict = {
    'errors': [{
        'title': 'Invalid DOI',
        'detail': 'DOI not found: invalid-doi',
        'status': '404'
    }]
}


CATEGORISATION_BY_DOI_API_EXAMPLE_RESPONSES: dict = {
    200: {
        'content': {
            'application/json': {
                'example': CATEGORISATION_BY_DOI_API_EXAMPLE_200_RESPONSE
            }
        }
    },
    404: {
        'model': JsonApiErrorsResponseDict,
        'content': {
            'application/json': {
                'example': CATEGORISATION_BY_DOI_API_EXAMPLE_404_RESPONSE
            }
        }
    }
}


CATEGORISATION_LIST_API_EXAMPLE_200_RESPONSE: CategorisationResponseDict = {
    'data': [{
        'display_name': 'Neuroscience',
        'type': 'category',
        'source_id': 'crossref_group_title'
    }, {
        'display_name': 'Pain Medicine',
        'type': 'category',
        'source_id': 'crossref_group_title'
    }]
}


CATEGORISATION_LIST_API_EXAMPLE_RESPONSES: dict = {
    200: {
        'content': {
            'application/json': {
                'example': CATEGORISATION_LIST_API_EXAMPLE_200_RESPONSE
            }
        }
    }
}


ARTICLES_BY_CATEGORY_API_EXAMPLE_200_RESPONSE: ArticleSearchResponseDict = {
    'data': [{
        'doi': '10.12345/example_1'
    }, {
        'doi': '10.12345/example_2'
    }]
}


ARTICLES_BY_CATEGORY_API_EXAMPLE_RESPONSES: dict = {
    200: {
        'content': {
            'application/json': {
                'example': ARTICLES_BY_CATEGORY_API_EXAMPLE_200_RESPONSE
            }
        }
    }
}


def get_not_found_error_json_response_dict(
    exception: ArticleDoiNotFoundError
) -> JsonApiErrorsResponseDict:
    return {
        'errors': [{
            'title': 'Invalid DOI',
            'detail': f'DOI not found: {exception.article_doi}',
            'status': '404'
        }]
    }


def get_not_found_error_json_response(
    exception: ArticleDoiNotFoundError
) -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(
        get_not_found_error_json_response_dict(exception),
        status_code=404
    )


def create_api_categorisation_router(
    app_providers_and_models: AppProvidersAndModels
) -> fastapi.APIRouter:
    router = fastapi.APIRouter()
    async_opensearch_categories_provider = AsyncOpenSearchCategoriesProvider(
        app_providers_and_models=app_providers_and_models
    )

    @router.get(
        '/categorisation/v1/categories',
        response_model=CategorisationResponseDict,
        responses=CATEGORISATION_LIST_API_EXAMPLE_RESPONSES
    )
    async def categories_list(
        request: fastapi.Request,
        evaluated_only: bool = False
    ):
        return await (
            async_opensearch_categories_provider
            .get_categorisation_list_response_dict(
                filter_parameters=OpenSearchFilterParameters(
                    evaluated_only=evaluated_only
                ),
                headers=get_cache_control_headers_for_request(request)
            )
        )

    @router.get(
        '/categorisation/v1/categories/by/doi',
        response_model=CategorisationResponseDict,
        responses=CATEGORISATION_BY_DOI_API_EXAMPLE_RESPONSES
    )
    async def categories_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        try:
            return await (
                async_opensearch_categories_provider
                .get_categorisation_response_dict_by_doi(
                    article_doi=article_doi,
                    headers=get_cache_control_headers_for_request(request)
                )
            )
        except ArticleDoiNotFoundError as exc:
            return get_not_found_error_json_response(exc)

    @router.get(
        '/categorisation/v1/articles/by/category',
        response_model=ArticleSearchResponseDict,
        responses=ARTICLES_BY_CATEGORY_API_EXAMPLE_RESPONSES
    )
    async def articles_by_category(
        request: fastapi.Request,
        category: str,
        evaluated_only: bool = False
    ):
        return await (
            async_opensearch_categories_provider
            .get_article_search_response_dict_by_category(
                category=category,
                filter_parameters=OpenSearchFilterParameters(
                    evaluated_only=evaluated_only
                ),
                sort_parameters=get_default_article_search_sort_parameters(
                    evaluated_only=evaluated_only
                ),
                headers=get_cache_control_headers_for_request(request)
            )
        )

    return router