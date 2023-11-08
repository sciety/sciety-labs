import ipaddress
from typing import Optional

from fastapi import Request


def get_likely_client_ip_for_request(request: Request) -> Optional[str]:
    """
    Returns a likely client IP for anlytics purpose withing GTM.
    In particular to identify Cookiebot where the user agent isn't reflecting it.
    The may be spoofable.
    """
    original_forwarded_for_value = request.headers.get('x-original-forwarded-for')
    if original_forwarded_for_value:
        for value in original_forwarded_for_value.split(','):
            value = value.strip()
            try:
                ip_address = ipaddress.ip_address(value)
            except ValueError:
                continue
            if not ip_address.is_private:
                return value
    real_ip_value = request.headers.get('x-real-ip')
    if real_ip_value:
        return real_ip_value
    if request.client:
        return request.client.host
    return None
