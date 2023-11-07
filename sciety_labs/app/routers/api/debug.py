import logging

from fastapi import APIRouter, Request


LOGGER = logging.getLogger(__name__)


def create_api_debug_router():
    router = APIRouter()

    @router.get('/debug', include_in_schema=False)
    def debug_data(request: Request):
        result: dict = {
            'headers': request.headers
        }
        if request.client:
            result.update({
                'client.host': request.client.host,
                'client.port': request.client.port
            })
        return result

    return router
