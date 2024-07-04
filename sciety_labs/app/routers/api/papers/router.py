import logging
import textwrap
from typing import Optional, Sequence, Tuple

import fastapi

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.api.utils.jsonapi import (
    AsyncExceptionHandlerMappingT,
    JsonApiRoute
)
from sciety_labs.app.routers.api.utils.jsonapi_typing import JsonApiErrorsResponseDict
from sciety_labs.app.routers.api.utils.validation import InvalidApiFieldsError, validate_api_fields
from sciety_labs.app.routers.api.papers.providers import (
    INTERNAL_ARTICLE_FIELDS_BY_API_FIELD_NAME,
    DoiNotFoundError,
    AsyncOpenSearchPapersProvider,
    get_default_paper_search_sort_parameters
)
from sciety_labs.app.routers.api.papers.typing import (
    PaperSearchResponseDict,
    ClassificationResponseDict
)
from sciety_labs.providers.opensearch.utils import (
    OpenSearchFilterParameters,
    OpenSearchPaginationParameters,
    OpenSearchSortField,
    OpenSearchSortParameters
)
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request
from sciety_labs.utils.text import parse_csv


LOGGER = logging.getLogger(__name__)


CATEGORISATION_BY_DOI_API_EXAMPLE_200_RESPONSE: ClassificationResponseDict = {
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


CATEGORISATION_LIST_API_EXAMPLE_200_RESPONSE: ClassificationResponseDict = {
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

PREPRINTS_BY_CATEGORY_API_EXAMPLE_200_RESPONSE: PaperSearchResponseDict = {
    'data': [{
        'type': 'paper',
        'id': EXAMPLE_DOI_1,
        'attributes': {
            'doi': EXAMPLE_DOI_1
        }
    }, {
        'type': 'paper',
        'id': EXAMPLE_DOI_2,
        'attributes': {
            'doi': EXAMPLE_DOI_2
        }
    }]
}


PREPRINTS_BY_CATEGORY_API_EXAMPLE_RESPONSES: dict = {
    200: {
        'content': {
            'application/json': {
                'example': PREPRINTS_BY_CATEGORY_API_EXAMPLE_200_RESPONSE
            }
        }
    }
}


DEFAULT_PAPER_FIELDS = {'doi'}


ALL_PAPER_FIELDS = list(INTERNAL_ARTICLE_FIELDS_BY_API_FIELD_NAME.keys())

ALL_PAPER_FIELDS_CSV = ','.join(ALL_PAPER_FIELDS)

ALL_PAPER_FIELDS_AS_MARKDOWN_LIST = '\n'.join([
    f'- `{field_name}`'
    for field_name in ALL_PAPER_FIELDS
])

PAPER_FIELDS_FASTAPI_QUERY = fastapi.Query(
    alias='fields[paper]',
    default=','.join(sorted(DEFAULT_PAPER_FIELDS)),
    description='\n'.join([
        'Comma separated list of fields. The following fields can be retrieved:',
        '',
        ALL_PAPER_FIELDS_AS_MARKDOWN_LIST,
        '',
        'To retrieve all fields, use:',
        f'`{ALL_PAPER_FIELDS_CSV}`'
    ]),
    examples=[  # Note: These only seem to appear in /redoc
        'doi',
        ALL_PAPER_FIELDS_CSV
    ]
)

SUPPORTED_API_PAPER_SORT_FIELDS = [
    'publication_date'
]

OPENSEARCH_FIELDS_BY_API_SORT_FIELD = {
    'publication_date': 'europepmc.first_publication_date'
}

SUPPORTED_PREFIXED_API_PAPER_SORT_FIELDS = [
    f'{sord_order_prefix}{field_name}'
    for sord_order_prefix in ['', '-']
    for field_name in SUPPORTED_API_PAPER_SORT_FIELDS
]

SUPPORTED_API_PAPER_SORT_FIELDS_AS_MARKDOWN_LIST = '\n'.join([
    f'- `{field_name}`'
    for field_name in SUPPORTED_API_PAPER_SORT_FIELDS
])

PAPER_SEARCH_SORT_FIELDS_FASTAPI_QUERY = fastapi.Query(
    alias='sort',
    default='',
    description='\n'.join([
        'By default, sorting will be by score (descending).',
        '',
        'Comma separated list of fields to sort by.',
        'The sort order for each sort field is ascending unless it is prefixed with a minus.',
        '',
        'The following fields can be specified to sort by:',
        '',
        SUPPORTED_API_PAPER_SORT_FIELDS_AS_MARKDOWN_LIST,
        '',
        'For example to sort by publication date descending, specify: `-publication_date`'
    ]),
    examples=[  # Note: These only seem to appear in /redoc
        '-publication_date'
    ]
)


PREPRINTS_SEARCH_API_DESCRIPTION = textwrap.dedent(
    '''
    Searches for preprints matching the provided `query`.
    Results are sorted by relevance.

    Known limitations:
    - Only searches preprints with EuropePMC metadata in OpenSearch
    '''
)


def get_doi_not_found_error_json_response_dict(
    exception: DoiNotFoundError
) -> JsonApiErrorsResponseDict:
    return {
        'errors': [{
            'title': 'Invalid DOI',
            'detail': f'DOI not found: {exception.doi}',
            'status': '404'
        }]
    }


async def handle_doi_not_found_error(
    request: fastapi.Request,  # pylint: disable=unused-argument
    exc: DoiNotFoundError
) -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(
        get_doi_not_found_error_json_response_dict(exc),
        status_code=404
    )


def get_invalid_api_fields_json_response_dict(
    exception: InvalidApiFieldsError
) -> JsonApiErrorsResponseDict:
    return {
        'errors': [{
            'title': 'Invalid fields',
            'detail': (
                'Invalid fields specified: '
                + ','.join(exception.invalid_field_names)
            ),
            'status': '400',
            'source': {'parameter': exception.query_parameter_name}
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
    DoiNotFoundError: handle_doi_not_found_error,
    InvalidApiFieldsError: handle_invalid_api_fields_error
}


class PapersJsonApiRoute(JsonApiRoute):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            exception_handler_mapping=EXCEPTION_HANDLER_MAPPING
        )


def get_prefix_and_api_sort_field_for_prefixed_api_sort_field(
    prefixed_api_paper_sort_field: str
) -> Tuple[str, str]:
    if prefixed_api_paper_sort_field.startswith('-'):
        return '-', prefixed_api_paper_sort_field[1:]
    return '', prefixed_api_paper_sort_field


def get_opensearch_sort_field_for_api_paper_sort_field(
    prefixed_api_paper_sort_field: str
) -> OpenSearchSortField:
    prefix, api_paper_sort_field = (
        get_prefix_and_api_sort_field_for_prefixed_api_sort_field(
            prefixed_api_paper_sort_field
        )
    )
    return OpenSearchSortField(
        field_name=OPENSEARCH_FIELDS_BY_API_SORT_FIELD[
            api_paper_sort_field
        ],
        sort_order=(
            'desc' if prefix == '-' else 'asc'
        )
    )


def get_opensearch_sort_parameters_for_api_paper_sort_field_list(
    prefixed_api_paper_sort_fields: Sequence[str]
) -> OpenSearchSortParameters:
    return OpenSearchSortParameters(sort_fields=[
        get_opensearch_sort_field_for_api_paper_sort_field(
            api_paper_sort_field
        )
        for api_paper_sort_field in prefixed_api_paper_sort_fields
    ])


def create_api_papers_router(
    app_providers_and_models: AppProvidersAndModels
) -> fastapi.APIRouter:
    router = fastapi.APIRouter(
        route_class=PapersJsonApiRoute,
        tags=['papers']
    )

    async_opensearch_papers_provider = AsyncOpenSearchPapersProvider(
        app_providers_and_models=app_providers_and_models
    )

    @router.get(
        '/papers/v1/preprints/classifications',
        response_model=ClassificationResponseDict,
        responses=CATEGORISATION_LIST_API_EXAMPLE_RESPONSES
    )
    async def classifications_list(
        request: fastapi.Request,
        evaluated_only: bool = fastapi.Query(alias='filter[evaluated_only]', default=False)
    ):
        return await (
            async_opensearch_papers_provider
            .get_classification_list_response_dict(
                filter_parameters=OpenSearchFilterParameters(
                    evaluated_only=evaluated_only
                ),
                headers=get_cache_control_headers_for_request(request)
            )
        )

    @router.get(
        '/papers/v1/preprints/classifications/by/doi/{doi:path}',
        response_model=ClassificationResponseDict,
        responses=CATEGORISATION_BY_DOI_API_EXAMPLE_RESPONSES
    )
    async def classifications_by_doi(
        request: fastapi.Request,
        doi: str
    ):
        return await (
            async_opensearch_papers_provider
            .get_classificiation_response_dict_by_doi(
                doi=doi,
                headers=get_cache_control_headers_for_request(request)
            )
        )

    @router.get(
        '/papers/v1/preprints',
        response_model=PaperSearchResponseDict,
        responses=PREPRINTS_BY_CATEGORY_API_EXAMPLE_RESPONSES
    )
    async def preprints(  # pylint: disable=too-many-arguments
        request: fastapi.Request,
        category: Optional[str] = fastapi.Query(alias='filter[category]', default=None),
        evaluated_only: bool = fastapi.Query(alias='filter[evaluated_only]', default=False),
        page_size: int = fastapi.Query(alias='page[size]', default=10),
        page_number: int = fastapi.Query(alias='page[number]', ge=1, default=1),
        api_paper_fields_csv: str = PAPER_FIELDS_FASTAPI_QUERY
    ):
        api_paper_fields_set = set(api_paper_fields_csv.split(','))
        validate_api_fields(
            api_paper_fields_set,
            valid_values=ALL_PAPER_FIELDS,
            query_parameter_name=PAPER_FIELDS_FASTAPI_QUERY.alias
        )
        return await (
            async_opensearch_papers_provider
            .get_paper_search_response_dict(
                filter_parameters=OpenSearchFilterParameters(
                    category=category,
                    evaluated_only=evaluated_only
                ),
                sort_parameters=get_default_paper_search_sort_parameters(
                    evaluated_only=evaluated_only
                ),
                pagination_parameters=OpenSearchPaginationParameters(
                    page_size=page_size,
                    page_number=page_number
                ),
                paper_fields_set=api_paper_fields_set,
                headers=get_cache_control_headers_for_request(request)
            )
        )

    @router.get(
        '/papers/v1/preprints/search',
        description=PREPRINTS_SEARCH_API_DESCRIPTION,
        response_model=PaperSearchResponseDict,
        responses=PREPRINTS_BY_CATEGORY_API_EXAMPLE_RESPONSES
    )
    async def preprints_search(  # pylint: disable=too-many-arguments
        request: fastapi.Request,
        query: str = fastapi.Query(min_length=3),
        category: Optional[str] = fastapi.Query(alias='filter[category]', default=None),
        evaluated_only: bool = fastapi.Query(alias='filter[evaluated_only]', default=False),
        page_size: int = fastapi.Query(alias='page[size]', default=10),
        page_number: int = fastapi.Query(alias='page[number]', ge=1, default=1),
        api_paper_fields_csv: str = PAPER_FIELDS_FASTAPI_QUERY,
        prefixed_api_paper_sort_fields_csv: str = PAPER_SEARCH_SORT_FIELDS_FASTAPI_QUERY
    ):
        LOGGER.info('prefixed_api_paper_sort_fields_csv: %r', prefixed_api_paper_sort_fields_csv)
        api_paper_fields_set = set(api_paper_fields_csv.split(','))
        validate_api_fields(
            api_paper_fields_set,
            valid_values=ALL_PAPER_FIELDS,
            query_parameter_name=PAPER_FIELDS_FASTAPI_QUERY.alias
        )
        api_paper_sort_fields = parse_csv(prefixed_api_paper_sort_fields_csv)
        LOGGER.debug('api_paper_sort_fields: %r', api_paper_sort_fields)
        validate_api_fields(
            set(api_paper_sort_fields),
            valid_values=SUPPORTED_PREFIXED_API_PAPER_SORT_FIELDS,
            query_parameter_name=PAPER_SEARCH_SORT_FIELDS_FASTAPI_QUERY.alias
        )
        return await (
            async_opensearch_papers_provider
            .get_paper_search_response_dict(
                filter_parameters=OpenSearchFilterParameters(
                    category=category,
                    evaluated_only=evaluated_only
                ),
                sort_parameters=(
                    get_opensearch_sort_parameters_for_api_paper_sort_field_list(
                        api_paper_sort_fields
                    )
                ),
                pagination_parameters=OpenSearchPaginationParameters(
                    page_size=page_size,
                    page_number=page_number
                ),
                paper_fields_set=api_paper_fields_set,
                query=query,
                headers=get_cache_control_headers_for_request(request)
            )
        )

    return router
