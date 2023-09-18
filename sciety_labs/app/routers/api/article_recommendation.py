import logging

from fastapi import APIRouter


LOGGER = logging.getLogger(__name__)


def create_api_article_recommendation_router():
    router = APIRouter()

    @router.get('/api/like/s2/recommendations/v1/papers/forpaper/DOI:{article_doi}')
    def like_s2_recommendations_for_paper(
        article_doi: str
    ):
        return {'article_doi': article_doi}

    return router
