import logging
from typing import Awaitable, Callable, Mapping, Type, TypeVar

import fastapi

from sciety_labs.app.routers.api.categorisation.typing import JsonApiErrorsResponseDict


LOGGER = logging.getLogger(__name__)


ExceptionT = TypeVar('ExceptionT', bound=Exception)


AsyncExceptionHandlerCallable = Callable[
    [fastapi.Request, ExceptionT],
    Awaitable[fastapi.responses.JSONResponse]
]


AsyncExceptionHandlerMappingT = Mapping[
    Type[Exception],
    AsyncExceptionHandlerCallable
]


def get_default_jsonapi_error_json_response_dict(
    exception: Exception
) -> JsonApiErrorsResponseDict:
    return {
        'errors': [{
            'title': 'Exception',
            'detail': repr(exception),
            'status': '500'
        }]
    }


async def default_async_jsonapi_exception_handler(
    request: fastapi.Request,  # pylint: disable=unused-argument
    exc: Exception
) -> fastapi.responses.JSONResponse:
    return fastapi.responses.JSONResponse(
        get_default_jsonapi_error_json_response_dict(exc),
        status_code=400
    )


def get_async_exception_handler(
    exc: Exception,
    exception_handler_mapping: AsyncExceptionHandlerMappingT,
    default_exception_handler: AsyncExceptionHandlerCallable
) -> AsyncExceptionHandlerCallable:
    LOGGER.debug('type(exc)=%r', type(exc))
    LOGGER.debug('exception_handler_mapping=%r', exception_handler_mapping)
    exception_handler = exception_handler_mapping.get(type(exc))
    if exception_handler is not None:
        LOGGER.debug('Found exception handler for %r (%r)', type(exc), exception_handler)
        return exception_handler
    LOGGER.debug('Falling back to default exception handler for %r', type(exc))
    return default_exception_handler


async def async_handle_exception_and_return_response(
    request: fastapi.Request,
    exc: Exception,
    exception_handler_mapping: AsyncExceptionHandlerMappingT,
    default_exception_handler: AsyncExceptionHandlerCallable
) -> fastapi.responses.JSONResponse:
    exception_handler = get_async_exception_handler(
        exc,
        exception_handler_mapping=exception_handler_mapping,
        default_exception_handler=default_exception_handler
    )
    return await exception_handler(request, exc)
