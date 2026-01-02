from datetime import datetime

import requests
from requests_cache import CachedResponse

from sciety_labs.utils.datetime import get_utc_timestamp_with_tzinfo, get_utcnow


def get_response_timestamp(response: requests.Response) -> datetime:
    if isinstance(response, CachedResponse):
        return get_utc_timestamp_with_tzinfo(response.created_at)
    return get_utcnow()
