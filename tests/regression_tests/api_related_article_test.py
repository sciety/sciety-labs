

from requests import Session
from sciety_labs.app.routers.api.article_recommendation import S2RecommendationResponseDict

from tests.regression_tests.test_data import DOI_1


class TestRelatedArticlesApi:
    def test_should_load_related_article_results(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/api/like/s2/recommendations/v1/papers/forpaper/DOI:{DOI_1}'
        )
        response.raise_for_status()
        response_json: S2RecommendationResponseDict = response.json()
        assert len(response_json['recommendedPapers']) > 0
