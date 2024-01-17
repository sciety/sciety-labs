from fastapi import FastAPI

from sciety_labs.utils.fastapi import update_request_scope_to_original_url_middleware
from sciety_labs.utils.uvicorn import (
    RedirectDoubleQueryStringMiddleware,
    RedirectPathMappingMiddleware
)


REDIRECT_PATH_MAPPING: dict[str, str] = {
    '/favicon.ico': '/static/sciety/images/favicons/generated/favicon.ico',
    '/apple-touch-icon.png': '/static/sciety/images/favicons/generated/apple-touch-icon.png'
}


def add_app_middlware(app: FastAPI):
    app.middleware('http')(update_request_scope_to_original_url_middleware)

    app.add_middleware(RedirectDoubleQueryStringMiddleware)

    app.add_middleware(
        RedirectPathMappingMiddleware,
        path_mapping=REDIRECT_PATH_MAPPING
    )
