import json
import logging
from datetime import date, timedelta
from typing import Any, Iterable, Mapping, Optional, Sequence, cast

from typing_extensions import NotRequired, TypedDict

import numpy.typing as npt

from opensearchpy import OpenSearch
import opensearchpy
from sciety_labs.models.article import ArticleMetaData, ArticleStats

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList,
    SingleArticleRecommendationProvider
)
from sciety_labs.providers.crossref import CrossrefMetaDataProvider
from sciety_labs.providers.semantic_scholar import (
    SemanticScholarTitleAbstractEmbeddingVectorProvider
)
from sciety_labs.utils.datetime import get_utcnow
from sciety_labs.utils.distance import cosine_similarity


LOGGER = logging.getLogger(__name__)


DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS = 50


class DocumentS2AuthorDict(TypedDict):
    name: str
    s2_author_id: NotRequired[str]


class DocumentS2Dict(TypedDict):
    title: str
    author_list: NotRequired[Sequence[DocumentS2AuthorDict]]


class DocumentEuropePmcCollectiveAuthorDict(TypedDict):
    collective_name: NotRequired[str]


class DocumentEuropePmcIndividualAuthorDict(TypedDict):
    full_name: NotRequired[str]
    initials: NotRequired[str]
    last_name: NotRequired[str]
    first_name: NotRequired[str]


class DocumentEuropePmcAuthorDict(
    DocumentEuropePmcCollectiveAuthorDict,
    DocumentEuropePmcIndividualAuthorDict
):
    pass


class DocumentEuropePmcDict(TypedDict):
    title_with_markup: NotRequired[str]
    first_publication_date: NotRequired[str]
    author_list: NotRequired[Sequence[DocumentEuropePmcAuthorDict]]


class DocumentScietyDict(TypedDict):
    evaluation_count: NotRequired[int]


class DocumentDict(TypedDict):
    doi: str
    s2: NotRequired[DocumentS2Dict]
    europepmc: NotRequired[DocumentEuropePmcDict]
    sciety: NotRequired[DocumentScietyDict]


def get_author_names_for_document_s2_authors(
    authors: Optional[Sequence[DocumentS2AuthorDict]]
) -> Optional[Sequence[str]]:
    if authors is None:
        return None
    return [author['name'] for author in authors]


def get_author_name_for_document_europepmc_author(
    author: DocumentEuropePmcAuthorDict
) -> str:
    name: Optional[str] = (
        author.get('collective_name')
        or author.get('full_name')
    )
    if not name:
        raise AssertionError(f'no name found in {repr(author)}')
    return name


def get_author_names_for_document_europepmc_authors(
    authors: Optional[Sequence[DocumentEuropePmcAuthorDict]]
) -> Optional[Sequence[str]]:
    if authors is None:
        return None
    return [get_author_name_for_document_europepmc_author(author) for author in authors]


def get_optional_date_from_str(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    return date.fromisoformat(date_str)


def get_article_meta_from_document(
    document: DocumentDict
) -> ArticleMetaData:
    article_doi = document['doi']
    assert article_doi
    europepmc_data: Optional[DocumentEuropePmcDict] = document.get('europepmc')
    s2_data: Optional[DocumentS2Dict] = document.get('s2')
    article_title = (
        (europepmc_data and europepmc_data.get('title_with_markup'))
        or (s2_data and s2_data.get('title'))
    )
    assert article_title is not None
    return ArticleMetaData(
        article_doi=article_doi,
        article_title=article_title,
        published_date=get_optional_date_from_str(
            europepmc_data.get('first_publication_date') if europepmc_data else None
        ),
        author_name_list=(
            get_author_names_for_document_europepmc_authors(
                europepmc_data.get('author_list') if europepmc_data else None
            )
            or get_author_names_for_document_s2_authors(
                s2_data.get('author_list') if s2_data else None
            )
        )
    )


def get_value_for_key_path(parent: dict, key_path: Sequence[str]) -> Optional[Any]:
    result: Any = parent
    for key in key_path:
        result = result.get(key)
    return result


def get_embedding_vector_from_document_or_none(
    document: DocumentDict,
    embedding_vector_mapping_name: Optional[str] = None
) -> Optional[Sequence[float]]:
    if embedding_vector_mapping_name:
        embedding_vector_mapping_path = embedding_vector_mapping_name.split('.')
        return cast(
            Sequence[float],
            get_value_for_key_path(
                cast(dict, document),
                embedding_vector_mapping_path
            )
        )
    return None


def _get_article_recommendation_score_or_none(
    document: DocumentDict,
    embedding_vector_mapping_name: Optional[str] = None,
    query_vector: Optional[npt.ArrayLike] = None
) -> Optional[float]:
    if query_vector is not None:
        embedding_vector = get_embedding_vector_from_document_or_none(
            document,
            embedding_vector_mapping_name
        )
        if embedding_vector is not None:
            return cosine_similarity(embedding_vector, query_vector)
    return None


def get_article_recommendation_from_document(
    document: DocumentDict,
    embedding_vector_mapping_name: Optional[str] = None,
    query_vector: Optional[npt.ArrayLike] = None
) -> ArticleRecommendation:
    article_meta = get_article_meta_from_document(document)
    sciety_data: Optional[DocumentScietyDict] = document.get('sciety')
    evaluation_count = sciety_data.get('evaluation_count') if sciety_data else None
    article_stats = (
        ArticleStats(evaluation_count=evaluation_count)
        if evaluation_count is not None
        else None
    )
    return ArticleRecommendation(
        article_doi=article_meta.article_doi,
        article_meta=article_meta,
        article_stats=article_stats,
        score=_get_article_recommendation_score_or_none(
            document,
            embedding_vector_mapping_name=embedding_vector_mapping_name,
            query_vector=query_vector
        )
    )


def iter_article_recommendation_from_opensearch_hits(
    hits: Iterable[dict],
    embedding_vector_mapping_name: Optional[str] = None,
    query_vector: Optional[npt.ArrayLike] = None
) -> Iterable[ArticleRecommendation]:
    for hit in hits:
        yield get_article_recommendation_from_document(
            hit['_source'],
            embedding_vector_mapping_name=embedding_vector_mapping_name,
            query_vector=query_vector
        )


def get_vector_search_query(  # pylint: disable=too-many-arguments
    query_vector: npt.ArrayLike,
    embedding_vector_mapping_name: str,
    max_results: int,
    filter_parameters: ArticleRecommendationFilterParameters
) -> dict:
    vector_query_part: dict = {
        'vector': query_vector,
        'k': max_results
    }
    bool_filter: dict = {}
    if filter_parameters.exclude_article_dois:
        bool_filter.setdefault('must_not', []).append({
            'ids': {'values': sorted(filter_parameters.exclude_article_dois)}
        })
    if filter_parameters.from_publication_date:
        bool_filter.setdefault('must', []).append({
            'range': {
                'europepmc.first_publication_date': {
                    'gte': filter_parameters.from_publication_date.isoformat()
                }
            }
        })
    if filter_parameters.evaluated_only:
        bool_filter.setdefault('must', []).append({
            'range': {'sciety.evaluation_count': {'gte': 1}}
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
        client_search_results = (
            self.opensearch_client.search(  # pylint: disable=unexpected-keyword-arg
                body=search_query,
                index=index,
                _source_includes=source_includes,
                headers=headers
            )
        )
        hits = client_search_results['hits']['hits'][:max_results]
        return hits

    def get_embedding_vector_for_article_doi(
        self,
        article_doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> Optional[Sequence[float]]:
        try:
            doc = self.opensearch_client.get_source(
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
        embedding_vector = doc.get(self.embedding_vector_mapping_name)
        if not embedding_vector or len(embedding_vector) == 0:
            LOGGER.info('Article has no embedding vector in OpenSearch index: %r', article_doi)
            return None
        return embedding_vector

    def get_alternative_embedding_vector_for_article_doi_via_title_and_abstract(
        self,
        article_doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> Optional[Sequence[float]]:
        article_meta = self.crossref_metadata_provider.get_article_metadata_by_doi(
            article_doi,
            headers=headers
        )
        if not article_meta.article_title or not article_meta.abstract:
            LOGGER.info('No title or abstract available to get embedding vector')
            return None
        LOGGER.info('Retrieving embedding vector via title and abstract')
        return self.title_abstract_embedding_vector_provider.get_embedding_vector(
            title=article_meta.article_title,
            abstract=article_meta.abstract,
            headers=headers
        )

    def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None,
        filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleRecommendationList:
        if not max_recommendations:
            max_recommendations = DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS
        LOGGER.info('max_recommendations: %r', max_recommendations)
        embedding_vector = self.get_embedding_vector_for_article_doi(article_doi, headers=headers)
        if embedding_vector is None:
            embedding_vector = (
                self.get_alternative_embedding_vector_for_article_doi_via_title_and_abstract(
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
        hits = self._run_vector_search_and_get_hits(
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
