# pylint: disable=duplicate-code
import json
import logging
from datetime import date, timedelta
from typing import Mapping, Optional, Sequence

import numpy.typing as npt

import opensearchpy

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList
)
from sciety_labs.providers.async_article_recommendation import (
    AsyncSingleArticleRecommendationProvider
)
from sciety_labs.providers.async_crossref import AsyncCrossrefMetaDataProvider
from sciety_labs.providers.async_semantic_scholar import (
    AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider
)
from sciety_labs.providers.opensearch_article_recommendation import (
    DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS,
    get_vector_search_query,
    iter_article_recommendation_from_opensearch_hits
)
from sciety_labs.utils.datetime import get_utcnow


LOGGER = logging.getLogger(__name__)


class AsyncOpenSearchArticleRecommendation(AsyncSingleArticleRecommendationProvider):
    def __init__(  # pylint: disable=too-many-arguments
        self,
        opensearch_client: opensearchpy.AsyncOpenSearch,
        index_name: str,
        embedding_vector_mapping_name: str,
        crossref_metadata_provider: AsyncCrossrefMetaDataProvider,
        title_abstract_embedding_vector_provider: (
            AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider
        )
    ):
        self.opensearch_client = opensearch_client
        self.index_name = index_name
        self.embedding_vector_mapping_name = embedding_vector_mapping_name
        self.crossref_metadata_provider = crossref_metadata_provider
        self.title_abstract_embedding_vector_provider = title_abstract_embedding_vector_provider

    async def _run_vector_search_and_get_hits(  # pylint: disable=too-many-arguments
        self,
        query_vector: npt.ArrayLike,
        index: str,
        embedding_vector_mapping_name: str,
        source_includes: Sequence[str],
        max_results: int,
        filter_parameters: ArticleRecommendationFilterParameters,
        headers: Optional[Mapping[str, str]] = None
    ) -> Sequence[dict]:
        search_query = get_vector_search_query(
            query_vector=query_vector,
            embedding_vector_mapping_name=embedding_vector_mapping_name,
            max_results=max_results,
            filter_parameters=filter_parameters
        )
        LOGGER.info('search_query JSON: %s (headers=%r)', json.dumps(search_query), headers)
        client_search_results = await (
            self.opensearch_client.search(  # pylint: disable=unexpected-keyword-arg
                body=search_query,
                index=index,
                _source_includes=source_includes,
                headers=headers
            )
        )
        hits = client_search_results['hits']['hits'][:max_results]
        return hits

    async def get_embedding_vector_for_article_doi(
        self,
        article_doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> Optional[Sequence[float]]:
        try:
            doc = await self.opensearch_client.get_source(
                index=self.index_name,
                id=article_doi,
                _source_includes=[self.embedding_vector_mapping_name],
                headers=headers
            )
        except opensearchpy.exceptions.NotFoundError:
            doc = None
        if not doc:
            LOGGER.info('Article not found in OpenSearch index: %r', article_doi)
            return None
        LOGGER.debug('Getting embedding vector from OpenSearch doc')
        embedding_vector = doc.get(self.embedding_vector_mapping_name)
        if not embedding_vector or len(embedding_vector) == 0:
            LOGGER.info('Article has no embedding vector in OpenSearch index: %r', article_doi)
            return None
        return embedding_vector

    async def get_alternative_embedding_vector_for_article_doi_via_title_and_abstract(
        self,
        article_doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> Optional[Sequence[float]]:
        article_meta = await self.crossref_metadata_provider.get_article_metadata_by_doi(
            article_doi,
            headers=headers
        )
        if not article_meta.article_title or not article_meta.abstract:
            LOGGER.info('No title or abstract available to get embedding vector')
            return None
        LOGGER.info('Retrieving embedding vector via title and abstract')
        return await self.title_abstract_embedding_vector_provider.get_embedding_vector(
            title=article_meta.article_title,
            abstract=article_meta.abstract,
            headers=headers
        )

    async def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None,
        filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleRecommendationList:
        if not max_recommendations:
            max_recommendations = DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS
        LOGGER.info(
            (
                'Async getting related articles for'
                ' (article_doi=%r, filter_parameters=%r, max_recommendations=%r, headers=%r)'
            ),
            article_doi,
            filter_parameters,
            max_recommendations,
            headers
        )
        embedding_vector = await self.get_embedding_vector_for_article_doi(
            article_doi,
            headers=headers
        )
        LOGGER.info('Embedding vector from OpenSearch (%r): %r', article_doi, embedding_vector)
        if embedding_vector is not None:
            LOGGER.info(
                'Embedding vector found in OpenSearch for: %r (size: %d)',
                article_doi,
                len(embedding_vector)
            )
        else:
            LOGGER.info(
                (
                    'No embedding vector found in OpenSearch,'
                    ' trying to get via title and abstract: %r'
                ),
                article_doi
            )
            embedding_vector = (
                await self.get_alternative_embedding_vector_for_article_doi_via_title_and_abstract(
                    article_doi,
                    headers=headers
                )
            )
        if embedding_vector is None:
            return ArticleRecommendationList([], get_utcnow())
        LOGGER.info('Found embedding vector: %d', len(embedding_vector))
        if filter_parameters is None:
            filter_parameters = ArticleRecommendationFilterParameters(
                exclude_article_dois={article_doi},
                from_publication_date=date.today() - timedelta(days=60)
            )
        LOGGER.info('filter_parameters: %r', filter_parameters)
        hits = await self._run_vector_search_and_get_hits(
            embedding_vector,
            index=self.index_name,
            embedding_vector_mapping_name=self.embedding_vector_mapping_name,
            source_includes=[
                'doi',
                's2.title',
                's2.author_list',
                'europepmc.first_publication_date',
                'europepmc.title_with_markup',
                'europepmc.author_list',
                'sciety.evaluation_count',
                self.embedding_vector_mapping_name,
            ],
            max_results=max_recommendations,
            filter_parameters=filter_parameters,
            headers=headers
        )
        LOGGER.debug('hits: %r', hits)
        recommendations = list(iter_article_recommendation_from_opensearch_hits(
            hits,
            embedding_vector_mapping_name=self.embedding_vector_mapping_name,
            query_vector=embedding_vector
        ))[:max_recommendations]
        LOGGER.info('hits: %d, recommendations: %d', len(hits), len(recommendations))
        return ArticleRecommendationList(recommendations, get_utcnow())
