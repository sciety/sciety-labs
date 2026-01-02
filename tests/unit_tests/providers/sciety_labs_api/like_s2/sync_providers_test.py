from unittest.mock import ANY, MagicMock

import pytest
import requests

from sciety_labs.models.article import KnownDoiPrefix
from sciety_labs.providers.interfaces.article_recommendation import (
    ArticleRecommendationFilterParameters
)
from sciety_labs.providers.sciety_labs_api.like_s2.sync_providers import (
    ScietyLabsApiSingleArticleRecommendationProvider
)


ARTICLE_DOI_1 = '10.1234/example.doi.1'

PREPRINT_DOI_PREFIX_1 = KnownDoiPrefix.BIORXIV_MEDRXIV

S2_RECOMMENDED_PAPER_DICT_1: dict = {
    'externalIds': {
        'DOI': f'{PREPRINT_DOI_PREFIX_1}/recommended.doi.1'
    },
    'title': 'Recommended Paper 1',
    '_score': 0.90
}


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
            url=expected_url,
            params={
                'fields': 'externalIds,title'
            },
            headers=sciety_labs_api_single_article_recommendation_provider.get_headers(
                headers=None
            )
        )

    def test_should_pass_max_recommendations_to_api(
        self,
        sciety_labs_api_single_article_recommendation_provider:
            ScietyLabsApiSingleArticleRecommendationProvider,
        requests_session_mock: MagicMock
    ) -> None:
        (
            sciety_labs_api_single_article_recommendation_provider
            .get_article_recommendation_list_for_article_doi(
                article_doi=ARTICLE_DOI_1,
                max_recommendations=5
            )
        )

        requests_session_mock.get.assert_called_once_with(
            url=ANY,
            params={
                'fields': ANY,
                'limit': 5
            },
            headers=ANY
        )

    def test_should_pass_evaluated_only_filter_to_api(
        self,
        sciety_labs_api_single_article_recommendation_provider:
            ScietyLabsApiSingleArticleRecommendationProvider,
        requests_session_mock: MagicMock
    ) -> None:
        (
            sciety_labs_api_single_article_recommendation_provider
            .get_article_recommendation_list_for_article_doi(
                article_doi=ARTICLE_DOI_1,
                filter_parameters=(
                    ArticleRecommendationFilterParameters(
                        evaluated_only=True
                    )
                )
            )
        )

        requests_session_mock.get.assert_called_once_with(
            url=ANY,
            params={
                'fields': ANY,
                '_evaluated_only': 'true'
            },
            headers=ANY
        )

    def test_should_parse_recommendation_response(
        self,
        sciety_labs_api_single_article_recommendation_provider:
            ScietyLabsApiSingleArticleRecommendationProvider,
        requests_session_mock: MagicMock
    ) -> None:
        requests_session_mock.get.return_value.json.return_value = {
            'recommendedPapers': [
                S2_RECOMMENDED_PAPER_DICT_1
            ]
        }
        article_recommendation_list = (
            sciety_labs_api_single_article_recommendation_provider
            .get_article_recommendation_list_for_article_doi(
                article_doi=ARTICLE_DOI_1
            )
        )
        assert article_recommendation_list is not None
        assert len(article_recommendation_list.recommendations) == 1
        first_recommendation = article_recommendation_list.recommendations[0]
        assert first_recommendation.article_doi == (
            S2_RECOMMENDED_PAPER_DICT_1['externalIds']['DOI']
        )
        assert first_recommendation.article_meta is not None
        assert first_recommendation.article_meta.article_title == (
            S2_RECOMMENDED_PAPER_DICT_1['title']
        )
