from typing import Iterable
from unittest.mock import MagicMock, patch
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sciety_labs.app.routers.api import article_recommendation as module_under_test
from sciety_labs.app.routers.api.article_recommendation import (
    create_api_article_recommendation_router,
    get_s2_recommended_paper_response_for_article_recommendation,
    get_s2_recommended_papers_response_for_article_recommendation_list
)
from sciety_labs.providers.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationList
)
from sciety_labs.utils.datetime import get_utcnow


DOI_1 = 'doi1'


@pytest.fixture(name='get_article_recommendation_list_for_article_dois_mock', autouse=True)
def _get_article_recommendation_list_for_article_dois_mock() -> Iterable[MagicMock]:
    with patch.object(
        module_under_test,
        'get_article_recommendation_list_for_article_dois'
    ) as mock:
        yield mock


@pytest.fixture(name='app_providers_and_models_mock')
def _app_providers_and_models_mock() -> MagicMock:
    return MagicMock(name='app_providers_and_models')


@pytest.fixture(name='test_client')
def _test_client(app_providers_and_models_mock: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(create_api_article_recommendation_router(
        app_providers_and_models=app_providers_and_models_mock
    ))
    return TestClient(app)


class TestGetS2RecommendedPaperResponseForArticleRecommendation:
    def test_should_return_response_for_paper_without_metadata(self):
        result = get_s2_recommended_paper_response_for_article_recommendation(
            ArticleRecommendation(
                article_doi=DOI_1
            )
        )
        assert result == {
            'externalIds': {'DOI': DOI_1}
        }


class TestGetS2RecommendedPapersResponseForArticleRecommendationList:
    def test_should_return_empty_papers_list(self):
        result = get_s2_recommended_papers_response_for_article_recommendation_list(
            ArticleRecommendationList(
                recommendations=[],
                recommendation_timestamp=get_utcnow()
            )
        )
        assert result == {'recommendedPapers': []}

    def test_should_return_single_recommended_paper_without_metadata(self):
        article_recommendation = ArticleRecommendation(
            article_doi=DOI_1
        )
        result = get_s2_recommended_papers_response_for_article_recommendation_list(
            ArticleRecommendationList(
                recommendations=[article_recommendation],
                recommendation_timestamp=get_utcnow()
            )
        )
        assert result == {'recommendedPapers': [
            get_s2_recommended_paper_response_for_article_recommendation(
                article_recommendation
            )
        ]}


class TestArticleRecommendationApi:
    def test_should_return_404_if_paper_id_was_missing(self, test_client: TestClient):
        response = test_client.get('/api/like/s2/recommendations/v1/papers/forpaper')
        assert response.status_code == 404

    def test_should_return_404_if_paper_id_is_not_starting_with_doi(self, test_client: TestClient):
        response = test_client.get('/api/like/s2/recommendations/v1/papers/forpaper/123456')
        assert response.status_code == 404

    def test_should_return_200_if_doi_was_specified(self, test_client: TestClient):
        response = test_client.get(f'/api/like/s2/recommendations/v1/papers/forpaper/DOI:{DOI_1}')
        assert response.status_code == 200

    def test_should_pass_article_doi_to_get_article_recommendation_list_for_article_dois(
        self,
        test_client: TestClient,
        app_providers_and_models_mock: MagicMock,
        get_article_recommendation_list_for_article_dois_mock: MagicMock
    ):
        test_client.get(f'/api/like/s2/recommendations/v1/papers/forpaper/DOI:{DOI_1}')
        get_article_recommendation_list_for_article_dois_mock.assert_called_with(
            [DOI_1],
            app_providers_and_models=app_providers_and_models_mock,
            max_recommendations=None
        )

    def test_should_format_recommendation_response(
        self,
        test_client: TestClient,
        get_article_recommendation_list_for_article_dois_mock: MagicMock
    ):
        article_recommendation_list = ArticleRecommendationList(
            recommendations=[],
            recommendation_timestamp=get_utcnow()
        )
        get_article_recommendation_list_for_article_dois_mock.return_value = (
            article_recommendation_list
        )
        get_s2_recommended_papers_response_for_article_recommendation_list(
            article_recommendation_list
        )
        response = test_client.get(
            f'/api/like/s2/recommendations/v1/papers/forpaper/DOI:{DOI_1}'
        )
        assert response.status_code == 200
        assert response.json() == (
            get_s2_recommended_papers_response_for_article_recommendation_list(
                article_recommendation_list
            )
        )
