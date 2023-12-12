import logging
import threading
import anyio

from fastapi import APIRouter, Request


LOGGER = logging.getLogger(__name__)


def create_api_debug_router():
    router = APIRouter()

    @router.get('/debug', include_in_schema=False)
    async def debug_data(request: Request):
        result: dict = {
            'headers': request.headers,
            'threading.active_count': threading.active_count(),
            'max_thread_count': (
                anyio.to_thread.current_default_thread_limiter().total_tokens
            )
        }
        if request.client:
            result.update({
                'client.host': request.client.host,
                'client.port': request.client.port
            })
        return result

    return router
