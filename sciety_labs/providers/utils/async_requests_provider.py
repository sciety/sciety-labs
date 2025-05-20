from contextlib import asynccontextmanager
import logging
from time import monotonic
from typing import Dict, Mapping, Optional

import aiohttp

from sciety_labs.utils.aio import get_response_cache_timestamp
from sciety_labs.utils.datetime import get_timestamp_as_isoformat
from sciety_labs.utils.http_headers import get_merged_headers


LOGGER = logging.getLogger(__name__)


class AsyncRequestsProvider:
    def __init__(
        self,
        client_session: Optional[aiohttp.ClientSession] = None
    ) -> None:
        self.headers: Dict[str, str] = {
            'User-Agent': 'Sciety Labs; +https://github.com/sciety/sciety-labs'
        }
        if client_session is None:
            client_session = aiohttp.ClientSession()
        self.client_session = client_session
        self.timeout = aiohttp.ClientTimeout(total=5 * 60)

    def get_headers(
        self,
        headers: Optional[Mapping[str, str]] = None
    ) -> Mapping[str, str]:
        return get_merged_headers(self.headers, headers)

    @asynccontextmanager
    async def request(self, method: str, url: str, **kwargs):
        start_time = monotonic()
        async with self.client_session.request(
            method,
            url,
            **kwargs
        ) as response:
            end_time = monotonic()
            cache_timestamp = get_response_cache_timestamp(response)
            LOGGER.info(
                'Response: method=%r, url=%r, status=%d, took=%.3fs, cached=%r'
                ', cache_timestamp=%r',
                response.request_info.method,
                response.request_info.url,
                response.status,
                (end_time - start_time),
                (cache_timestamp is not None),
                get_timestamp_as_isoformat(cache_timestamp)
            )
            yield response

    def get(self, url: str, **kwargs):
        return self.request(aiohttp.hdrs.METH_GET, url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request(aiohttp.hdrs.METH_POST, url, **kwargs)
