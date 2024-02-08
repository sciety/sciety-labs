

from requests import Session

from tests.regression_tests.test_data import FEED_NAME_1
from tests.regression_tests.test_utils import ResponseWrapper


class TestListOfFeedsPage:
    def test_should_load_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/feeds',
        )
        response.raise_for_status()
        assert ResponseWrapper(response).get_article_card_count() > 0


class TestFeedPage:
    def test_should_load_feed_page(
        self,
        regression_test_session: Session
    ):
        response = regression_test_session.get(
            f'/feeds/by-name/{FEED_NAME_1}'
        )
        response.raise_for_status()
        assert ResponseWrapper(response).get_article_card_count() > 0

    def test_should_load_feed_rss(
        self,
        regression_test_session: Session
    ):
        response = regression_test_session.get(
            f'/feeds/by-name/{FEED_NAME_1}/atom.xml'
        )
        response.raise_for_status()
