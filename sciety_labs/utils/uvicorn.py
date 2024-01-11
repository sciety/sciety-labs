import logging

from starlette.datastructures import URL, Headers
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send


LOGGER = logging.getLogger(__name__)


class RedirectToHostMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        preferred_host: str
    ) -> None:
        self.app = app
        assert preferred_host
        self.preferred_host = preferred_host

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = Headers(scope=scope)
        host = headers.get('host', '')
        LOGGER.info('Host: %r', host)
        is_valid_host = host == self.preferred_host

        if is_valid_host:
            await self.app(scope, receive, send)
        else:
            url = URL(scope=scope)
            redirect_url = url.replace(netloc=self.preferred_host)
            response = RedirectResponse(url=str(redirect_url))
            await response(scope, receive, send)
