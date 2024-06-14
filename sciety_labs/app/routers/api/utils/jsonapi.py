import logging
from types import MappingProxyType
from typing import Awaitable, Callable, Mapping, Optional, Type, TypeVar

import fastapi

from sciety_labs.app.routers.api.utils.jsonapi_typing import JsonApiErrorsResponseDict


LOGGER = logging.getLogger(__name__)


ExceptionT = TypeVar('ExceptionT', bound=Exception)
RequestHandlerCallableT = TypeVar('RequestHandlerCallableT', bound=Callable)


AsyncExceptionHandlerCallable = Callable[
    [fastapi.Request, ExceptionT],
    Awaitable[fastapi.responses.JSONResponse]
]


AsyncExceptionHandlerMappingT = Mapping[
    Type[Exception],
    AsyncExceptionHandlerCallable
]


EMPTY_EXCEPTION_HANDLER_MAPPING: AsyncExceptionHandlerMappingT = MappingProxyType({})


def get_http_exception_jsonapi_error_json_response(
    exception: fastapi.exceptions.HTTPException
) -> fastapi.responses.JSONResponse:
    response_json: JsonApiErrorsResponseDict = {
        'errors': [{
            'title': type(exception).__name__,
            'detail': exception.detail,
            'status': str(exception.status_code)
        }]
    }
    return fastapi.responses.JSONResponse(
        response_json,
        status_code=exception.status_code
    )


def get_request_validation_jsonapi_error_json_response(
    exception: fastapi.exceptions.RequestValidationError
) -> fastapi.responses.JSONResponse:
    response_json: JsonApiErrorsResponseDict = {
        'errors': [{
            'title': type(exception).__name__,
            'detail': (
                'Encountered validation errors. Please check the request.'
            ),
            'status': '400',
            'meta': {
                'errors': exception.errors(),
            }
        }]
    }
    return fastapi.responses.JSONResponse(
        response_json,
        status_code=400
    )


def get_generic_jsonapi_error_json_response(
    exception: Exception
) -> fastapi.responses.JSONResponse:
    error_message: Optional[str] = None
    try:
        error_message = str(exception)
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    if not error_message:
        try:
            error_message = repr(exception)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    response_json: JsonApiErrorsResponseDict = {
        'errors': [{
            'title': type(exception).__name__,
            'detail': error_message or 'Oops',
            'status': '500'
        }]
    }
    return fastapi.responses.JSONResponse(
        response_json,
        status_code=500
    )


def get_default_jsonapi_error_json_response(
    exception: Exception
) -> fastapi.responses.JSONResponse:
    if isinstance(exception, fastapi.exceptions.HTTPException):
        return get_http_exception_jsonapi_error_json_response(exception)

    if isinstance(exception, fastapi.exceptions.RequestValidationError):
        return get_request_validation_jsonapi_error_json_response(exception)

    return get_generic_jsonapi_error_json_response(exception)


async def default_async_jsonapi_exception_handler(
    request: fastapi.Request,  # pylint: disable=unused-argument
    exc: Exception
) -> fastapi.responses.JSONResponse:
    return get_default_jsonapi_error_json_response(exc)


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


class JsonApiRoute(fastapi.routing.APIRoute):
    def __init__(
        self,
        *args,
        exception_handler_mapping: AsyncExceptionHandlerMappingT = (
            EMPTY_EXCEPTION_HANDLER_MAPPING
        ),
        default_exception_handler: AsyncExceptionHandlerCallable = (
            default_async_jsonapi_exception_handler
        ),
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.exception_handler_mapping = exception_handler_mapping
        self.default_exception_handler = default_exception_handler

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: fastapi.Request) -> fastapi.Response:
            try:
                LOGGER.debug('handling request: %r', request)
                return await original_route_handler(request)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                return await async_handle_exception_and_return_response(
                    request,
                    exc,
                    exception_handler_mapping=self.exception_handler_mapping,
                    default_exception_handler=self.default_exception_handler
                )

        return custom_route_handler
