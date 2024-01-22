from starlette.datastructures import URL

from sciety_labs.utils.uvicorn import get_redirect_url_for_double_query_string_url_or_none


BASE_URL_1 = 'https://localhost/path/to'


class TestGetRedirectUrlForDoubleQueryStringUrlOrNone:
    def test_should_return_none_for_url_with_no_query_parameters(self):
        redirect_url = get_redirect_url_for_double_query_string_url_or_none(
            URL(BASE_URL_1)
        )
        assert redirect_url is None

    def test_should_return_none_for_url_with_regular_query_parameters(self):
        redirect_url = get_redirect_url_for_double_query_string_url_or_none(
            URL(f'{BASE_URL_1}?param1=1&param2=2')
        )
        assert redirect_url is None

    def test_should_return_url_without_duplicate_query_parameters(self):
        redirect_url = get_redirect_url_for_double_query_string_url_or_none(
            URL(f'{BASE_URL_1}?param1=1&param2=2?param1=1&param2=2')
        )
        assert redirect_url == f'{BASE_URL_1}?param1=1&param2=2'

    def test_should_return_url_without_duplicate_url_encoded_query_parameters(self):
        redirect_url = get_redirect_url_for_double_query_string_url_or_none(
            URL(f'{BASE_URL_1}?param1=1&param2=2%3Fparam1%3D1&param2%3D2')
        )
        assert redirect_url == f'{BASE_URL_1}?param1=1&param2=2'
