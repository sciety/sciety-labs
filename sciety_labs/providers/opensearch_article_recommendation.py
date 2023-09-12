import logging
from typing import Optional

from opensearchpy import OpenSearch

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendationList,
    SingleArticleRecommendationProvider
)
from sciety_labs.utils.datetime import get_utcnow


LOGGER = logging.getLogger(__name__)


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
        get_result = self.opensearch_client.get(
            index=self.index_name,
            id=article_doi,
            _source_includes=['s2_specter_embedding_v1']
        )
        doc = get_result.get('_source')
        if not doc:
            LOGGER.info('Article not found in OpenSearch index: %r', article_doi)
            return ArticleRecommendationList([], get_utcnow())
        embedding_vector = doc.get('s2_specter_embedding_v1')
        if not embedding_vector or len(embedding_vector) == 0:
            LOGGER.info('Article has no embedding vector in OpenSearch index: %r', article_doi)
            return ArticleRecommendationList([], get_utcnow())
        LOGGER.info('Found embedding vector: %d', len(embedding_vector))
        return ArticleRecommendationList([], get_utcnow())
