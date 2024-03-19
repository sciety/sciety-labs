from typing import Optional

import aiohttp
import requests


def get_exception_status_code(exception: Exception) -> Optional[int]:
    if isinstance(exception, requests.exceptions.RequestException):
        return (
            exception.response.status_code
            if exception.response is not None
            else None
        )
    if isinstance(exception, aiohttp.ClientResponseError):
        return exception.status
    return None
