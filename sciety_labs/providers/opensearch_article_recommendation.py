import logging
from typing import Iterable, Optional, Sequence

import numpy.typing as npt

from opensearchpy import OpenSearch
from sciety_labs.models.article import ArticleMetaData

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationList,
    SingleArticleRecommendationProvider
)
from sciety_labs.utils.datetime import get_utcnow


LOGGER = logging.getLogger(__name__)


DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS = 50


def get_article_meta_from_document(
    document: dict
) -> ArticleMetaData:
    article_doi = document['doi']
    assert article_doi
    return ArticleMetaData(
        article_doi=article_doi,
        article_title=document['title'],
        published_date=None,
        author_name_list=None
    )


def iter_article_recommendation_from_opensearch_hits(
    hits: Iterable[dict]
) -> Iterable[ArticleRecommendation]:
    for hit in hits:
        article_meta = get_article_meta_from_document(hit['_source'])
        yield ArticleRecommendation(
            article_doi=article_meta.article_doi,
            article_meta=article_meta
        )


class OpenSearchArticleRecommendation(SingleArticleRecommendationProvider):
    def __init__(
        self,
        opensearch_client: OpenSearch,
        index_name: str,
        embedding_vector_mapping_name: str = 's2_specter_embedding_v1'
    ):
        self.opensearch_client = opensearch_client
        self.index_name = index_name
        self.embedding_vector_mapping_name = embedding_vector_mapping_name

    def _run_vector_search_and_get_hits(  # pylint: disable=too-many-arguments
        self,
        query_vector: npt.ArrayLike,
        index: str,
        embedding_vector_mapping_name: str,
        source_includes: Sequence[str],
        max_results: int
    ) -> Sequence[dict]:
        search_query = {
            'query': {
                'knn': {
                    embedding_vector_mapping_name: {
                        'vector': query_vector,
                        'k': max_results
                    }
                }
            }
        }

        client_search_results = (
            self.opensearch_client.search(  # pylint: disable=unexpected-keyword-arg
                body=search_query,
                index=index,
                _source_includes=source_includes
            )
        )
        hits = client_search_results['hits']['hits'][:max_results]
        return hits

    def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None
    ) -> ArticleRecommendationList:
        get_result = self.opensearch_client.get(
            index=self.index_name,
            id=article_doi,
            _source_includes=[self.embedding_vector_mapping_name]
        )
        doc = get_result.get('_source')
        if not doc:
            LOGGER.info('Article not found in OpenSearch index: %r', article_doi)
            return ArticleRecommendationList([], get_utcnow())
        embedding_vector = doc.get(self.embedding_vector_mapping_name)
        if not embedding_vector or len(embedding_vector) == 0:
            LOGGER.info('Article has no embedding vector in OpenSearch index: %r', article_doi)
            return ArticleRecommendationList([], get_utcnow())
        LOGGER.info('Found embedding vector: %d', len(embedding_vector))
        hits = self._run_vector_search_and_get_hits(
            embedding_vector,
            index=self.index_name,
            embedding_vector_mapping_name=self.embedding_vector_mapping_name,
            source_includes=['doi', 'title'],
            max_results=3
        )
        LOGGER.info('hits: %r', hits)
        return ArticleRecommendationList(
            list(iter_article_recommendation_from_opensearch_hits(hits)),
            get_utcnow()
        )
