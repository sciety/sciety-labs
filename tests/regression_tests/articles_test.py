

from requests import Session

from tests.regression_tests.test_data import DOI_1
from tests.regression_tests.test_utils import ResponseWrapper


class TestArticlesPage:
    def test_should_load_article_by_doi_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/articles/by',
            params={'article_doi': DOI_1}
        )
        response.raise_for_status()

    def test_should_load_related_articles_by_doi_fragment(
        self,
        regression_test_session: Session
    ):
        response = regression_test_session.get(
            '/articles/article-recommendations/by',
            params={
                'article_doi': DOI_1,
                'fragment': 'true',
                'max_recommendations': '3',
                'enable_pagination': 'false'
            }
        )
        response.raise_for_status()
        assert ResponseWrapper(response).get_article_card_count() > 0

    def test_should_load_related_articles_by_doi_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/articles/article-recommendations/by',
            params={'article_doi': DOI_1}
        )
        response.raise_for_status()

    def test_should_load_related_articles_by_doi_fragment_with_pagination(
        self,
        regression_test_session: Session
    ):
        response = regression_test_session.get(
            '/articles/article-recommendations/by',
            params={
                'article_doi': DOI_1,
                'fragment': 'true'
            }
        )
        response.raise_for_status()
        assert ResponseWrapper(response).get_article_card_count() > 0
