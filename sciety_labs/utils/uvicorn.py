import logging
import re
from typing import Optional

from starlette.datastructures import URL
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send


LOGGER = logging.getLogger(__name__)


def get_redirect_url_for_double_query_string_url_or_none(url: URL) -> Optional[str]:
    LOGGER.debug('url.query: %r', url.query)
    if url.query:
        first_query_string, *other_query_strings = re.split(r'\?|%3F', url.query, maxsplit=1)
        if other_query_strings:
            return str(url.replace(query=first_query_string))
    return None


class RedirectDoubleQueryStringMiddleware:
    def __init__(
        self,
        app: ASGIApp
    ) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        LOGGER.debug('scope: %r', scope)
        url = URL(scope=scope)
        redirect_url = get_redirect_url_for_double_query_string_url_or_none(url)
        if redirect_url:
            LOGGER.info('Redirecting to (due to double query string): %r', redirect_url)
            response = RedirectResponse(url=redirect_url, status_code=301)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


class RedirectPathMappingMiddleware:
    def __init__(self, app: ASGIApp, path_mapping: dict[str, str]):
        self.app = app
        self.path_mapping = path_mapping

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        url = URL(scope=scope)
        redirect_to_path = self.path_mapping.get(url.path)

        if redirect_to_path:
            url = url.replace(path=redirect_to_path)
            response = RedirectResponse(url, status_code=301)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
