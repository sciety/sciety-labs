from unittest.mock import MagicMock

import starlette.datastructures

from sciety_labs.utils.fastapi import get_likely_client_ip_for_request


class TestGetLikelyClientIpForRequest:
    def test_should_return_none_without_forwarded_headers_and_no_client(self):
        request = MagicMock(name='request')
        request.client = None
        assert get_likely_client_ip_for_request(request=request) is None

    def test_should_return_client_host_if_available(self):
        request = MagicMock(name='request')
        request.client = starlette.datastructures.Address(host='host1', port=123)
        assert get_likely_client_ip_for_request(request=request) == 'host1'
