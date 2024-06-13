from requests import Session

from tests.regression_tests.test_utils import ResponseWrapper


class TestCategoriesListPage:
    def test_should_load_categories_list_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/categories'
        )
        response.raise_for_status()


class TestCategoriesArticlesPage:
    def test_should_load_categories_articles_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/categories/articles',
            params={'category': 'Neuroscience'}
        )
        response.raise_for_status()
        assert ResponseWrapper(response).get_article_card_count() > 0
