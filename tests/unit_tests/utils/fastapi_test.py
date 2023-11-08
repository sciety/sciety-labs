from unittest.mock import MagicMock

import pytest

import starlette.datastructures

from sciety_labs.utils.fastapi import get_likely_client_ip_for_request


IP_1 = '127.0.0.1'
IP_2 = '20.0.0.2'
IP_3 = '20.0.0.3'
IP_4 = '20.0.0.4'

PRIVATE_IP_1 = '10.0.0.1'


@pytest.fixture(name='request_mock')
def _request_mock() -> MagicMock:
    request = MagicMock(name='request')
    request.headers = starlette.datastructures.Headers()
    request.client = None
    return request


class TestGetLikelyClientIpForRequest:
    def test_should_return_none_without_forwarded_headers_and_no_client(
        self,
        request_mock: MagicMock
    ):
        request_mock.client = None
        assert get_likely_client_ip_for_request(request=request_mock) is None

    def test_should_return_client_host_if_available(
        self,
        request_mock: MagicMock
    ):
        request_mock.client = starlette.datastructures.Address(host=IP_1, port=123)
        assert get_likely_client_ip_for_request(request=request_mock) == IP_1

    def test_should_use_x_real_ip_if_available(
        self,
        request_mock: MagicMock
    ):
        request_mock.headers = starlette.datastructures.Headers({
            'x-real-ip': IP_2
        })
        request_mock.client = starlette.datastructures.Address(host=IP_1, port=123)
        assert get_likely_client_ip_for_request(request=request_mock) == IP_2

    def test_should_use_x_original_forwarded_for_if_available(
        self,
        request_mock: MagicMock
    ):
        request_mock.headers = starlette.datastructures.Headers({
            'x-real-ip': IP_2,
            'x-original-forwarded-for': IP_3
        })
        request_mock.client = starlette.datastructures.Address(host=IP_1, port=123)
        assert get_likely_client_ip_for_request(request=request_mock) == IP_3

    def test_should_pick_first_x_original_forwarded_for_value_if_not_private(
        self,
        request_mock: MagicMock
    ):
        request_mock.headers = starlette.datastructures.Headers({
            'x-real-ip': IP_2,
            'x-original-forwarded-for': f'{IP_3}, {IP_4}'
        })
        request_mock.client = starlette.datastructures.Address(host=IP_1, port=123)
        assert get_likely_client_ip_for_request(request=request_mock) == IP_3

    def test_should_pick_second_x_original_forwarded_for_value_if_first_value_is_private(
        self,
        request_mock: MagicMock
    ):
        request_mock.headers = starlette.datastructures.Headers({
            'x-real-ip': IP_2,
            'x-original-forwarded-for': f'{PRIVATE_IP_1}, {IP_4}'
        })
        request_mock.client = starlette.datastructures.Address(host=IP_1, port=123)
        assert get_likely_client_ip_for_request(request=request_mock) == IP_4

    def test_should_ignore_invalid_x_original_forwarded_for_value(
        self,
        request_mock: MagicMock
    ):
        request_mock.headers = starlette.datastructures.Headers({
            'x-real-ip': IP_2,
            'x-original-forwarded-for': 'invalid-ip'
        })
        request_mock.client = starlette.datastructures.Address(host=IP_1, port=123)
        assert get_likely_client_ip_for_request(request=request_mock) == IP_2
