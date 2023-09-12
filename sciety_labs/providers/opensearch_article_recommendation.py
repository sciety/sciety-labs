from typing import Optional

from opensearchpy import OpenSearch

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendationList,
    SingleArticleRecommendationProvider
)
from sciety_labs.utils.datetime import get_utcnow


DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS = 50


class OpenSearchArticleRecommendation(SingleArticleRecommendationProvider):
    def __init__(
        self,
        opensearch_client: OpenSearch,
        index_name: str
    ):
        self.opensearch_client = opensearch_client
        self.index_name = index_name

    def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None
    ) -> ArticleRecommendationList:
        return ArticleRecommendationList([], get_utcnow())
