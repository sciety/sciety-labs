from fastapi import FastAPI

from sciety_labs.utils.fastapi import update_request_scope_to_original_url_middleware
from sciety_labs.utils.uvicorn import RedirectDoubleQueryStringMiddleware


def add_app_middlware(app: FastAPI):
    app.middleware('http')(update_request_scope_to_original_url_middleware)

    app.add_middleware(RedirectDoubleQueryStringMiddleware)
