import logging
from typing import Mapping, Sequence

import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.api.utils.jsonapi import (
    AsyncExceptionHandlerMappingT,
    JsonApiRoute
)
from sciety_labs.app.routers.api.utils.jsonapi_typing import JsonApiErrorsResponseDict
from sciety_labs.app.routers.api.utils.validation import InvalidApiFieldsError, validate_api_fields
from sciety_labs.app.routers.api.classification.providers import (
    ArticleDoiNotFoundError,
    AsyncOpenSearchClassificationProvider,
    get_default_article_search_sort_parameters
)
from sciety_labs.app.routers.api.classification.typing import (
    ArticleSearchResponseDict,
    CategorisationResponseDict
)
from sciety_labs.models.article import InternalArticleFieldNames
from sciety_labs.providers.opensearch.utils import (
    OpenSearchFilterParameters,
    OpenSearchPaginationParameters
)
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request
from sciety_labs.utils.mapping import get_flat_mapped_values_or_all_values_for_mapping


LOGGER = logging.getLogger(__name__)


CATEGORISATION_BY_DOI_API_EXAMPLE_200_RESPONSE: CategorisationResponseDict = {
    'data': [{
        'type': 'category',
        'id': 'Pain Medicine',
        'attributes': {
            'display_name': 'Pain Medicine',
            'source_id': 'crossref_group_title'
        }
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
        'type': 'category',
        'id': 'Neuroscience',
        'attributes': {
            'display_name': 'Neuroscience',
            'source_id': 'crossref_group_title'
        }
    }, {
        'type': 'category',
        'id': 'Pain Medicine',
        'attributes': {
            'display_name': 'Pain Medicine',
            'source_id': 'crossref_group_title'
        }
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


EXAMPLE_DOI_1 = '10.12345/example_1'
EXAMPLE_DOI_2 = '10.12345/example_2'

ARTICLES_BY_CATEGORY_API_EXAMPLE_200_RESPONSE: ArticleSearchResponseDict = {
    'data': [{
        'type': 'article',
        'id': EXAMPLE_DOI_1,
        'attributes': {
            'doi': EXAMPLE_DOI_1
        }
    }, {
        'type': 'article',
        'id': EXAMPLE_DOI_2,
        'attributes': {
            'doi': EXAMPLE_DOI_2
        }
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


DEFAULT_ARTICLE_FIELDS = {'doi'}


INTERNAL_ARTICLE_FIELDS_BY_API_FIELD_NAME: Mapping[str, Sequence[str]] = {
    'doi': [InternalArticleFieldNames.ARTICLE_DOI],
    'title': [InternalArticleFieldNames.ARTICLE_TITLE],
    'publication_date': [InternalArticleFieldNames.PUBLISHED_DATE],
    'evaluation_count': [InternalArticleFieldNames.EVALUATION_COUNT],
    'latest_evaluation_activity_timestamp': [
        InternalArticleFieldNames.LATEST_EVALUATION_ACTIVITY_TIMESTAMP
    ]
}


ALL_ARTICLE_FIELDS = [
    'doi',
    'title',
    'publication_date',
    'evaluation_count',
    'latest_evaluation_activity_timestamp'
]

ALL_ARTICLE_FIELDS_CSV = ','.join(ALL_ARTICLE_FIELDS)

ALL_ARTICLE_FIELDS_AS_MARKDOWN_LIST = '\n'.join([
    f'- `{field_name}`'
    for field_name in ALL_ARTICLE_FIELDS
])

ARTICLE_FIELDS_FASTAPI_QUERY = fastapi.Query(
    alias='fields[article]',
    default=','.join(sorted(DEFAULT_ARTICLE_FIELDS)),
    description='\n'.join([
        'Comma separated list of fields. The following fields can be retrieved:',
        '',
        ALL_ARTICLE_FIELDS_AS_MARKDOWN_LIST,
        '',
        'To retrieve all fields, use:',
        f'`{ALL_ARTICLE_FIELDS_CSV}`'
    ]),
    examples=[  # Note: These only seem to appear in /redoc
        'doi',
        ALL_ARTICLE_FIELDS_CSV
    ]
)


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


async def handle_article_doi_not_found_error(
    request: fastapi.Request,  # pylint: disable=unused-argument
    exc: ArticleDoiNotFoundError
) -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(
        get_not_found_error_json_response_dict(exc),
        status_code=404
    )


def get_invalid_api_fields_json_response_dict(
    exception: InvalidApiFieldsError
) -> JsonApiErrorsResponseDict:
    return {
        'errors': [{
            'title': 'Invalid fields',
            'detail': f'Invalid API fields: {",".join(exception.invalid_field_names)}',
            'status': '400'
        }]
    }


async def handle_invalid_api_fields_error(
    request: fastapi.Request,  # pylint: disable=unused-argument
    exc: InvalidApiFieldsError
) -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(
        get_invalid_api_fields_json_response_dict(exc),
        status_code=400
    )


EXCEPTION_HANDLER_MAPPING: AsyncExceptionHandlerMappingT = {
    ArticleDoiNotFoundError: handle_article_doi_not_found_error,
    InvalidApiFieldsError: handle_invalid_api_fields_error
}


class CatergorisationJsonApiRoute(JsonApiRoute):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            exception_handler_mapping=EXCEPTION_HANDLER_MAPPING
        )


def create_api_classification_router(
    app_providers_and_models: AppProvidersAndModels
) -> fastapi.APIRouter:
    router = fastapi.APIRouter(
        route_class=CatergorisationJsonApiRoute
    )

    async_opensearch_classification_provider = AsyncOpenSearchClassificationProvider(
        app_providers_and_models=app_providers_and_models
    )

    @router.get(
        '/classification/v1/categories',
        response_model=CategorisationResponseDict,
        responses=CATEGORISATION_LIST_API_EXAMPLE_RESPONSES
    )
    async def categories_list(
        request: fastapi.Request,
        evaluated_only: bool = False
    ):
        return await (
            async_opensearch_classification_provider
            .get_classification_list_response_dict(
                filter_parameters=OpenSearchFilterParameters(
                    evaluated_only=evaluated_only
                ),
                headers=get_cache_control_headers_for_request(request)
            )
        )

    @router.get(
        '/classification/v1/categories/by/doi',
        response_model=CategorisationResponseDict,
        responses=CATEGORISATION_BY_DOI_API_EXAMPLE_RESPONSES
    )
    async def categories_by_doi(
        request: fastapi.Request,
        article_doi: str
    ):
        return await (
            async_opensearch_classification_provider
            .get_classificiation_response_dict_by_doi(
                article_doi=article_doi,
                headers=get_cache_control_headers_for_request(request)
            )
        )

    @router.get(
        '/classification/v1/articles/by/category',
        response_model=ArticleSearchResponseDict,
        responses=ARTICLES_BY_CATEGORY_API_EXAMPLE_RESPONSES
    )
    async def articles_by_category(  # pylint: disable=too-many-arguments
        request: fastapi.Request,
        category: str,
        evaluated_only: bool = False,
        page_size: int = fastapi.Query(alias='page[size]', default=10),
        page_number: int = fastapi.Query(alias='page[number]', ge=1, default=1),
        api_article_fields_csv: str = ARTICLE_FIELDS_FASTAPI_QUERY
    ):
        api_article_fields_set = set(api_article_fields_csv.split(','))
        validate_api_fields(api_article_fields_set, valid_values=ALL_ARTICLE_FIELDS)
        internal_article_fields_set = set(get_flat_mapped_values_or_all_values_for_mapping(
            INTERNAL_ARTICLE_FIELDS_BY_API_FIELD_NAME,
            api_article_fields_set
        ))
        return await (
            async_opensearch_classification_provider
            .get_article_search_response_dict_by_category(
                category=category,
                filter_parameters=OpenSearchFilterParameters(
                    evaluated_only=evaluated_only
                ),
                sort_parameters=get_default_article_search_sort_parameters(
                    evaluated_only=evaluated_only
                ),
                pagination_parameters=OpenSearchPaginationParameters(
                    page_size=page_size,
                    page_number=page_number
                ),
                article_fields_set=internal_article_fields_set,
                headers=get_cache_control_headers_for_request(request)
            )
        )

    return router
