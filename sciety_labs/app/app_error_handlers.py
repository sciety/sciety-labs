from http.client import HTTPException

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates

from sciety_labs.app.utils.common import (
    get_page_title
)


def add_app_error_handlers(
    app: FastAPI,
    templates: Jinja2Templates
):
    @app.exception_handler(404)
    async def not_found_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            request=request,
            name='errors/404.html',
            context={
                'page_title': get_page_title('Page not found'),
                'exception': exception
            },
            status_code=404
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_exception_handler(request: Request, exception: HTTPException):
        error_message = 'Something doesn\'t seem right, with the parameters.'
        return templates.TemplateResponse(
            request=request,
            name='errors/error.html',
            context={
                'page_title': get_page_title(error_message),
                'error_message': error_message,
                'exception': exception
            },
            status_code=400
        )

    @app.exception_handler(500)
    async def server_error_exception_handler(request: Request, exception: HTTPException):
        return templates.TemplateResponse(
            request=request,
            name='errors/500.html',
            context={
                'page_title': get_page_title('Something went wrong'),
                'exception': exception
            },
            status_code=500
        )
