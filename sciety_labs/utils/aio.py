from datetime import datetime
from typing import Optional

import aiohttp
from aiohttp_client_cache.response import CachedResponse

from sciety_labs.utils.datetime import get_utc_timestamp_with_tzinfo


def get_exception_status_code(exception: Exception) -> Optional[int]:
    if isinstance(exception, aiohttp.ClientResponseError):
        return exception.status
    return None


def get_response_cache_timestamp(response: aiohttp.ClientResponse) -> Optional[datetime]:
    if isinstance(response, CachedResponse):
        return get_utc_timestamp_with_tzinfo(response.created_at)
    return None
