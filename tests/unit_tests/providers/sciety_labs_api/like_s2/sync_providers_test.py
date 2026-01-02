from unittest.mock import MagicMock

import pytest
import requests

from sciety_labs.providers.sciety_labs_api.like_s2.sync_providers import (
    ScietyLabsApiSingleArticleRecommendationProvider
)


ARTICLE_DOI_1 = '10.1234/example.doi.1'


@pytest.fixture(name='response_mock')
def _response_mock() -> MagicMock:
    response_mock = MagicMock(requests.Response, name='response_mock')
    return response_mock


@pytest.fixture(name='requests_session_mock')
def _requests_session_mock(response_mock: MagicMock) -> MagicMock:
    requests_session_mock = MagicMock(requests.Session, name='requests_session_mock')
    requests_session_mock.get.return_value = response_mock
    return requests_session_mock


@pytest.fixture(name='sciety_labs_api_single_article_recommendation_provider')
def _sciety_labs_api_single_article_recommendation_provider(
    requests_session_mock: MagicMock
) -> ScietyLabsApiSingleArticleRecommendationProvider:
    return ScietyLabsApiSingleArticleRecommendationProvider(
        requests_session=requests_session_mock
    )


class TestScietyLabsApiSingleArticleRecommendationProvider:
    def test_should_request_recommendations_for_article_doi(
        self,
        sciety_labs_api_single_article_recommendation_provider:
            ScietyLabsApiSingleArticleRecommendationProvider,
        requests_session_mock: MagicMock
    ) -> None:
        expected_url = (
            'http://localhost:8000/api/like/s2/recommendations/v1/papers/forpaper/DOI:'
            + ARTICLE_DOI_1
        )

        (
            sciety_labs_api_single_article_recommendation_provider
            .get_article_recommendation_list_for_article_doi(
                article_doi=ARTICLE_DOI_1
            )
        )

        requests_session_mock.get.assert_called_once_with(
            url=expected_url
        )
