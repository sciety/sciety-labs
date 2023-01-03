import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


LOGGER = logging.getLogger(__name__)


def create_app():
    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static", html=False), name="static")
    app.mount("/", StaticFiles(directory="www_root", html=True), name="www_root")
    return app
