

from requests import Session

from tests.regression_tests.test_data import DOI_1


class TestHomePage:
    def test_should_load_home_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/',
            params={}
        )
        response.raise_for_status()
