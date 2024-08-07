

from requests import Session

from tests.regression_tests.test_utils import ResponseWrapper


class TestSearchPage:
    def test_should_load_search_page_without_search_term(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/search',
        )
        response.raise_for_status()

    def test_should_load_search_page_for_search_term_by_relevance_evaluated_only_europepmc(
        self,
        regression_test_session: Session
    ):
        response = regression_test_session.get(
            '/search',
            params={
                'category': 'articles',
                'query': 'covid',
                'evaluated_only': 'true',
                'sort_by': 'relevance',
                'date_range': '90d',
                'search_provider': 'europe_pmc'
            }
        )
        response.raise_for_status()
        assert ResponseWrapper(response).get_article_card_count() > 0

    def test_should_load_search_page_for_search_term_by_relevance_evaluated_only_sciety_labs(
        self,
        regression_test_session: Session
    ):
        response = regression_test_session.get(
            '/search',
            params={
                'category': 'articles',
                'query': 'covid',
                'evaluated_only': 'true',
                'sort_by': 'relevance',
                'date_range': '90d',
                'search_provider': 'sciety_labs'
            }
        )
        response.raise_for_status()
        assert ResponseWrapper(response).get_article_card_count() > 0
