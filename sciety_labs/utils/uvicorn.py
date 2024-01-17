import logging

from starlette.datastructures import URL
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send


LOGGER = logging.getLogger(__name__)


class RedirectDoubleQueryStringMiddleware:
    def __init__(
        self,
        app: ASGIApp
    ) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        LOGGER.debug('scope: %r', scope)
        url = URL(scope=scope)
        if url.query:
            first_query_string, *other_query_strings = url.query.split('?', maxsplit=1)
            if other_query_strings:
                redirect_url = str(url.replace(query=first_query_string))
                LOGGER.info('Redirecting to (due to double query string): %r', redirect_url)
                response = RedirectResponse(url=redirect_url, status_code=301)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)