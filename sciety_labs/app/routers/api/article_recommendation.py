import logging
from typing import Optional

from fastapi import APIRouter

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.recommendation import (
    get_article_recommendation_list_for_article_dois
)
from sciety_labs.providers.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationList
)


LOGGER = logging.getLogger(__name__)


def get_s2_recommended_paper_response_for_article_recommendation(
    article_recommendation: ArticleRecommendation
) -> dict:
    response: dict = {
        'externalIds': {
            'DOI': article_recommendation.article_doi
        }
    }
    article_meta = article_recommendation.article_meta
    if article_meta:
        response = {
            **response,
            'title': article_meta.article_title
        }
    return response


def get_s2_recommended_papers_response_for_article_recommendation_list(
    article_recommendation_list: ArticleRecommendationList
) -> dict:
    return {
        'recommendedPapers': [
            get_s2_recommended_paper_response_for_article_recommendation(
                article_recommendation
            )
            for article_recommendation in article_recommendation_list.recommendations
        ]
    }


def create_api_article_recommendation_router(
    app_providers_and_models: AppProvidersAndModels
):
    router = APIRouter()

    @router.get('/api/like/s2/recommendations/v1/papers/forpaper/DOI:{article_doi}')
    def like_s2_recommendations_for_paper(
        article_doi: str,
        limit: Optional[int] = None
    ):
        article_recommendation_list = get_article_recommendation_list_for_article_dois(
            [article_doi],
            app_providers_and_models=app_providers_and_models,
            max_recommendations=limit
        )
        return get_s2_recommended_papers_response_for_article_recommendation_list(
            article_recommendation_list
        )

    return router
