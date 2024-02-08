

from requests import Session


class TestHomePage:
    def test_should_load_home_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/',
            params={}
        )
        response.raise_for_status()
