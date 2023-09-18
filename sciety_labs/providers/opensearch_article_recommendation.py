import json
import logging
from datetime import date, timedelta
from typing import Iterable, Optional, Sequence, Set, TypedDict

import numpy.typing as npt

from opensearchpy import OpenSearch
import opensearchpy
from sciety_labs.models.article import ArticleMetaData

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationList,
    SingleArticleRecommendationProvider
)
from sciety_labs.providers.crossref import CrossrefMetaDataProvider
from sciety_labs.providers.semantic_scholar import (
    SemanticScholarTitleAbstractEmbeddingVectorProvider
)
from sciety_labs.utils.datetime import get_utcnow


LOGGER = logging.getLogger(__name__)


DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS = 50


class DocumentAuthor(TypedDict):
    name: str
    s2_author_id: Optional[str]


class DocumentDict(TypedDict):
    doi: str
    title: str
    authors: Optional[Sequence[DocumentAuthor]]


def get_author_names_for_document_authors(
    authors: Optional[Sequence[DocumentAuthor]]
) -> Optional[Sequence[str]]:
    if authors is None:
        return None
    return [author['name'] for author in authors]


def get_article_meta_from_document(
    document: DocumentDict
) -> ArticleMetaData:
    article_doi = document['doi']
    assert article_doi
    return ArticleMetaData(
        article_doi=article_doi,
        article_title=document['title'],
        published_date=None,
        author_name_list=get_author_names_for_document_authors(document.get('authors'))
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


def get_vector_search_query(
    query_vector: npt.ArrayLike,
    embedding_vector_mapping_name: str,
    max_results: int,
    exclude_article_dois: Optional[Set[str]] = None,
    from_publication_date: Optional[date] = None
) -> dict:
    vector_query_part: dict = {
        'vector': query_vector,
        'k': max_results
    }
    bool_filter: dict = {}
    if exclude_article_dois:
        bool_filter.setdefault('must_not', []).append({
            'ids': {'values': sorted(exclude_article_dois)}
        })
    if from_publication_date:
        bool_filter.setdefault('must', []).append({
            'range': {
                'publication_date': {'gte': from_publication_date.isoformat()}
            }
        })
    if bool_filter:
        vector_query_part = {
            **vector_query_part,
            'filter': {
                'bool': bool_filter
            }
        }
    search_query = {
        'size': max_results,
        'query': {
            'knn': {
                embedding_vector_mapping_name: vector_query_part
            }
        }
    }
    return search_query


class OpenSearchArticleRecommendation(SingleArticleRecommendationProvider):
    def __init__(  # pylint: disable=too-many-arguments
        self,
        opensearch_client: OpenSearch,
        index_name: str,
        embedding_vector_mapping_name: str,
        crossref_metadata_provider: CrossrefMetaDataProvider,
        title_abstract_embedding_vector_provider: (
            SemanticScholarTitleAbstractEmbeddingVectorProvider
        )
    ):
        self.opensearch_client = opensearch_client
        self.index_name = index_name
        self.embedding_vector_mapping_name = embedding_vector_mapping_name
        self.crossref_metadata_provider = crossref_metadata_provider
        self.title_abstract_embedding_vector_provider = title_abstract_embedding_vector_provider

    def _run_vector_search_and_get_hits(  # pylint: disable=too-many-arguments
        self,
        query_vector: npt.ArrayLike,
        index: str,
        embedding_vector_mapping_name: str,
        source_includes: Sequence[str],
        max_results: int,
        exclude_article_dois: Optional[Set[str]] = None,
        from_publication_date: Optional[date] = None
    ) -> Sequence[dict]:
        search_query = get_vector_search_query(
            query_vector=query_vector,
            embedding_vector_mapping_name=embedding_vector_mapping_name,
            max_results=max_results,
            exclude_article_dois=exclude_article_dois,
            from_publication_date=from_publication_date
        )
        LOGGER.info('search_query JSON: %s', json.dumps(search_query))
        client_search_results = (
            self.opensearch_client.search(  # pylint: disable=unexpected-keyword-arg
                body=search_query,
                index=index,
                _source_includes=source_includes
            )
        )
        hits = client_search_results['hits']['hits'][:max_results]
        return hits

    def get_embedding_vector_for_article_doi(
        self,
        article_doi: str
    ) -> Optional[Sequence[float]]:
        try:
            doc = self.opensearch_client.get_source(
                index=self.index_name,
                id=article_doi,
                _source_includes=[self.embedding_vector_mapping_name]
            )
        except opensearchpy.exceptions.NotFoundError:
            doc = None
        if not doc:
            LOGGER.info('Article not found in OpenSearch index: %r', article_doi)
            return None
        embedding_vector = doc.get(self.embedding_vector_mapping_name)
        if not embedding_vector or len(embedding_vector) == 0:
            LOGGER.info('Article has no embedding vector in OpenSearch index: %r', article_doi)
            return None
        return embedding_vector

    def get_alternative_embedding_vector_for_article_doi_via_title_and_abstract(
        self,
        article_doi: str,
    ) -> Optional[Sequence[float]]:
        article_meta = self.crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
        if not article_meta.article_title or not article_meta.abstract:
            LOGGER.info('No title or abstract available to get embedding vector')
            return None
        LOGGER.info('Retrieving embedding vector via title and abstract')
        return self.title_abstract_embedding_vector_provider.get_embedding_vector(
            title=article_meta.article_title,
            abstract=article_meta.abstract
        )

    def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None
    ) -> ArticleRecommendationList:
        if not max_recommendations:
            max_recommendations = DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS
        LOGGER.info('max_recommendations: %r', max_recommendations)
        embedding_vector = self.get_embedding_vector_for_article_doi(article_doi)
        if embedding_vector is None:
            embedding_vector = (
                self.get_alternative_embedding_vector_for_article_doi_via_title_and_abstract(
                    article_doi
                )
            )
        if embedding_vector is None:
            return ArticleRecommendationList([], get_utcnow())
        LOGGER.info('Found embedding vector: %d', len(embedding_vector))
        from_publication_date = date.today() - timedelta(days=60)
        LOGGER.info('from_publication_date: %r', from_publication_date)
        hits = self._run_vector_search_and_get_hits(
            embedding_vector,
            index=self.index_name,
            embedding_vector_mapping_name=self.embedding_vector_mapping_name,
            source_includes=['doi', 'title', 'authors'],
            max_results=max_recommendations,
            exclude_article_dois={article_doi},
            from_publication_date=from_publication_date
        )
        LOGGER.debug('hits: %r', hits)
        recommendations = list(iter_article_recommendation_from_opensearch_hits(
            hits
        ))[:max_recommendations]
        LOGGER.info('hits: %d, recommendations: %d', len(hits), len(recommendations))
        return ArticleRecommendationList(recommendations, get_utcnow())
