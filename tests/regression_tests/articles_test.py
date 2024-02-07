

from requests import Session

from tests.regression_tests.test_data import DOI_1


class TestArticlesPage:
    def test_should_load_article_by_doi_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/articles/by',
            params={'article_doi': DOI_1}
        )
        response.raise_for_status()
