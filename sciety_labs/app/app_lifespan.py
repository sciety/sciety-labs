from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels


LOGGER = logging.getLogger(__name__)


def add_app_lifespan_context(
    app: FastAPI,
    app_providers_and_models: AppProvidersAndModels
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):  # pylint: disable=unused-argument
        LOGGER.info('Start up')

        yield

        LOGGER.info('Shutting down, closing cached session')
        await app_providers_and_models.async_cached_client_session.close()
        LOGGER.info('Shutting down, done closing cached session')

    app.router.lifespan_context = lifespan
