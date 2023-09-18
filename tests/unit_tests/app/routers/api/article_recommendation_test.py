import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sciety_labs.app.routers.api.article_recommendation import (
    create_api_article_recommendation_router
)


DOI_1 = 'doi1'


@pytest.fixture(name='test_client')
def _test_client() -> TestClient:
    app = FastAPI()
    app.include_router(create_api_article_recommendation_router())
    return TestClient(app)


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
