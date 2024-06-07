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


def get_default_jsonapi_error_json_response_dict(
    exception: Exception
) -> JsonApiErrorsResponseDict:
    if isinstance(exception, fastapi.exceptions.HTTPException):
        return {
            'errors': [{
                'title': type(exception).__name__,
                'detail': exception.detail,
                'status': str(exception.status_code)
            }]
        }
    if isinstance(exception, fastapi.exceptions.RequestValidationError):
        return {
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
    error_message: Optional[str] = None
    try:
        error_message = str(exception)
    except Exception:
        pass
    if not error_message:
        try:
            error_message = repr(exception)
        except Exception:
            pass
    return {
        'errors': [{
            'title': type(exception).__name__,
            'detail': error_message or 'Oops',
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
