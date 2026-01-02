import logging
from typing import Mapping, Optional

from sciety_labs.providers.interfaces.article_recommendation import (
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList,
    SingleArticleRecommendationProvider
)
from sciety_labs.providers.utils.requests_provider import RequestsProvider
from sciety_labs.utils.datetime import get_utcnow


LOGGER = logging.getLogger(__name__)


class ScietyLabsApiSingleArticleRecommendationProvider(
    RequestsProvider,
    SingleArticleRecommendationProvider
):
    def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None,
        filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleRecommendationList:
        LOGGER.info(
            'Fetching article recommendations from Sciety Labs API for DOI: %r',
            article_doi
        )
        url = (
            'http://localhost:8000/api/like/s2/recommendations/v1/papers/forpaper/DOI:'
            + article_doi
        )
        self.requests_session.get(
            url=url
        )
        return ArticleRecommendationList(
            recommendations=[],
            recommendation_timestamp=get_utcnow()
        )
