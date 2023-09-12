from typing import Optional

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendationList,
    SingleArticleRecommendationProvider
)
from sciety_labs.utils.datetime import get_utcnow


DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS = 50


class OpenSearchArticleRecommendation(SingleArticleRecommendationProvider):
    def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None
    ) -> ArticleRecommendationList:
        return ArticleRecommendationList([], get_utcnow())
