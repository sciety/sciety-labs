import dataclasses
import logging
from datetime import date, timedelta
from typing import Any, Iterable, List, Literal, Mapping, Optional, Sequence, cast


import numpy.typing as npt

from sciety_labs.models.article import (
    ArticleMetaData,
    ArticleStats,
    InternalArticleFieldName,
    InternalArticleFieldNames,
    KnownDoiPrefix
)

from sciety_labs.providers.interfaces.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList
)
from sciety_labs.providers.opensearch.typing import (
    DocumentCrossrefAuthorDict,
    DocumentCrossrefDict,
    DocumentDict,
    DocumentEuropePmcAuthorDict,
    DocumentEuropePmcDict,
    DocumentS2AuthorDict,
    DocumentS2Dict,
    DocumentScietyDict
)
from sciety_labs.utils.datetime import get_utcnow
from sciety_labs.utils.distance import cosine_similarity


LOGGER = logging.getLogger(__name__)


DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS = 50


IS_EVALUATED_OPENSEARCH_FILTER_DICT = {
    'range': {'sciety.evaluation_count': {'gte': 1}}
}


DEFAULT_PAGE_SIZE = 10


@dataclasses.dataclass(frozen=True)
class OpenSearchFilterParameters:
    evaluated_only: bool = False
    category: Optional[str] = None
    from_publication_date: Optional[date] = None


@dataclasses.dataclass(frozen=True)
class OpenSearchSortField:
    field_name: str
    sort_order: Literal['asc', 'desc']

    def to_opensearch_sort_dict(self) -> dict:
        return {
            self.field_name: {
                'order': self.sort_order
            }
        }


@dataclasses.dataclass(frozen=True)
class OpenSearchSortParameters:
    sort_fields: Sequence[OpenSearchSortField] = dataclasses.field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.sort_fields)

    def to_opensearch_sort_dict_list(self) -> Sequence[dict]:
        return [
            sort_field.to_opensearch_sort_dict()
            for sort_field in self.sort_fields
        ]


@dataclasses.dataclass(frozen=True)
class OpenSearchPaginationParameters:
    page_size: int = DEFAULT_PAGE_SIZE
    page_number: int = 1

    def get_offset(self) -> int:
        return self.page_size * (self.page_number - 1)


def get_category_as_crossref_group_title_opensearch_filter_dict(
    category: str
) -> dict:
    return {
        'term': {
            'crossref.group_title.keyword': category
        }
    }


def get_opensearch_filter_dicts_for_filter_parameters(
    filter_parameters: OpenSearchFilterParameters
) -> Sequence[dict]:
    filter_dicts: List[dict] = []
    if filter_parameters.category:
        filter_dicts.extend([
            IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT,
            get_category_as_crossref_group_title_opensearch_filter_dict(
                filter_parameters.category
            )
        ])
    if filter_parameters.evaluated_only:
        filter_dicts.append(IS_EVALUATED_OPENSEARCH_FILTER_DICT)
    if filter_parameters.from_publication_date:
        filter_dicts.append(get_from_publication_date_query_filter(
            filter_parameters.from_publication_date
        ))
    return filter_dicts


def get_author_names_for_document_s2_authors(
    authors: Optional[Sequence[DocumentS2AuthorDict]]
) -> Optional[Sequence[str]]:
    if authors is None:
        return None
    return [author['name'] for author in authors]


def get_author_name_for_document_crossref_author(
    author: DocumentCrossrefAuthorDict
) -> str:
    name = f"{author.get('given_name')} {author.get('family_name')}".strip()
    if not name:
        raise AssertionError(f'no name found in {repr(author)}')
    return name


def get_author_names_for_document_crossref_authors(
    authors: Optional[Sequence[DocumentCrossrefAuthorDict]]
) -> Optional[Sequence[str]]:
    if authors is None:
        return None
    return [get_author_name_for_document_crossref_author(author) for author in authors]


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
    crossref_data: Optional[DocumentCrossrefDict] = document.get('crossref')
    europepmc_data: Optional[DocumentEuropePmcDict] = document.get('europepmc')
    s2_data: Optional[DocumentS2Dict] = document.get('s2')
    article_title = (
        (crossref_data and crossref_data.get('title_with_markup'))
        or (europepmc_data and europepmc_data.get('title_with_markup'))
        or (s2_data and s2_data.get('title'))
    )
    return ArticleMetaData(
        article_doi=article_doi,
        article_title=article_title,
        published_date=get_optional_date_from_str(
            (crossref_data.get('publication_date') if crossref_data else None)
            or (europepmc_data.get('first_publication_date') if europepmc_data else None)
        ),
        author_name_list=(
            get_author_names_for_document_crossref_authors(
                crossref_data.get('author_list') if crossref_data else None
            )
            or get_author_names_for_document_europepmc_authors(
                europepmc_data.get('author_list') if europepmc_data else None
            )
            or get_author_names_for_document_s2_authors(
                s2_data.get('author_list') if s2_data else None
            )
        )
    )


def get_article_stats_from_document(
    document: DocumentDict
) -> Optional[ArticleStats]:
    sciety_data: Optional[DocumentScietyDict] = document.get('sciety')
    evaluation_count = sciety_data.get('evaluation_count') if sciety_data else None
    return (
        ArticleStats(evaluation_count=evaluation_count)
        if evaluation_count is not None
        else None
    )


def get_value_for_key_path(parent: dict, key_path: Sequence[str]) -> Optional[Any]:
    result: Any = parent
    for key in key_path:
        if result is not None:
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
    article_stats = get_article_stats_from_document(document)
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


def get_from_publication_date_for_field_query_filter(
    field_name: str,
    from_publication_date: date
) -> dict:
    return {
        'range': {
            field_name: {
                'gte': from_publication_date.isoformat()
            }
        }
    }


def get_from_publication_date_query_filter(from_publication_date: date) -> dict:
    return get_from_publication_date_for_field_query_filter(
        field_name='calculated.publication_date',
        from_publication_date=from_publication_date
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
        bool_filter.setdefault('must', []).append(
            get_from_publication_date_query_filter(filter_parameters.from_publication_date)
        )
    if filter_parameters.evaluated_only:
        bool_filter.setdefault('must', []).append(IS_EVALUATED_OPENSEARCH_FILTER_DICT)
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


ARTICLE_TITLE_OPENSEARCH_FIELDS = [
    'crossref.title_with_markup',
    's2.title',
    'europepmc.title_with_markup'
]

AUTHOR_LIST_OPENSEARCH_FIELDS = [
    'crossref.author_list',
    's2.author_list',
    'europepmc.author_list'
]

PUBLISHED_DATE_OPENSEARCH_FIELDS = [
    'crossref.publication_date',
    'europepmc.first_publication_date'
]

EVALUATION_COUNT_OPENSEARCH_FIELDS = [
    'sciety.evaluation_count'
]

LATEST_EVALUATION_ACTIVITY_TIMESTAMP_OPENSEARCH_FIELDS = [
    'sciety.last_event_timestamp'
]


SUPPORTED_OPENSEARCH_FIELD_NAMES = (
    ['doi']
    + ARTICLE_TITLE_OPENSEARCH_FIELDS
    + AUTHOR_LIST_OPENSEARCH_FIELDS
    + PUBLISHED_DATE_OPENSEARCH_FIELDS
    + EVALUATION_COUNT_OPENSEARCH_FIELDS
    + LATEST_EVALUATION_ACTIVITY_TIMESTAMP_OPENSEARCH_FIELDS
)

OPENSEARCH_FIELDS_BY_REQUESTED_FIELD: Mapping[str, Sequence[str]] = {
    str(InternalArticleFieldNames.ARTICLE_DOI): ['doi'],
    str(InternalArticleFieldNames.ARTICLE_TITLE): ARTICLE_TITLE_OPENSEARCH_FIELDS,
    str(InternalArticleFieldNames.AUTHOR_NAME_LIST): AUTHOR_LIST_OPENSEARCH_FIELDS,
    str(InternalArticleFieldNames.PUBLISHED_DATE): PUBLISHED_DATE_OPENSEARCH_FIELDS,
    str(InternalArticleFieldNames.EVALUATION_COUNT): EVALUATION_COUNT_OPENSEARCH_FIELDS,
    str(InternalArticleFieldNames.LATEST_EVALUATION_ACTIVITY_TIMESTAMP): (
        LATEST_EVALUATION_ACTIVITY_TIMESTAMP_OPENSEARCH_FIELDS
    )
}


def get_source_includes_for_mapping(
    opensearch_fields_by_requested_field: Mapping[str, Sequence[str]],
    fields: Optional[Iterable[str]] = None
) -> Sequence[str]:
    if fields:
        return [
            opensearch_field
            for requested_field in fields
            for opensearch_field in opensearch_fields_by_requested_field[
                str(requested_field)
            ]
        ]
    return sorted({
        field_name
        for field_names in opensearch_fields_by_requested_field.values()
        for field_name in field_names
    })


def get_source_includes(
    embedding_vector_mapping_name: str,
    fields: Optional[Sequence[InternalArticleFieldName]] = None
) -> Sequence[str]:
    if fields:
        opensearch_fields_with_score_by_requested_field = {
            **OPENSEARCH_FIELDS_BY_REQUESTED_FIELD,
            str(InternalArticleFieldNames.SCORE): [embedding_vector_mapping_name]
        }
        return [
            opensearch_field
            for requested_field in fields
            for opensearch_field in opensearch_fields_with_score_by_requested_field[
                str(requested_field)
            ]
        ]
    return SUPPORTED_OPENSEARCH_FIELD_NAMES + [
        embedding_vector_mapping_name
    ]


def get_article_recommendation_list_from_opensearch_hits(
    hits: Sequence[dict],
    embedding_vector_mapping_name: str,
    query_vector: Optional[npt.ArrayLike],
    max_recommendations: int
) -> ArticleRecommendationList:
    LOGGER.debug('hits: %r', hits)
    recommendations = list(iter_article_recommendation_from_opensearch_hits(
        hits,
        embedding_vector_mapping_name=embedding_vector_mapping_name,
        query_vector=query_vector
    ))[:max_recommendations]
    LOGGER.info('hits: %d, recommendations: %d', len(hits), len(recommendations))
    return ArticleRecommendationList(recommendations, get_utcnow())


def get_default_filter_parameters(article_doi: str) -> ArticleRecommendationFilterParameters:
    return ArticleRecommendationFilterParameters(
        exclude_article_dois={article_doi},
        from_publication_date=date.today() - timedelta(days=60)
    )


IS_BIORXIV_MEDRXIV_DOI_PREFIX_OPENSEARCH_FILTER_DICT = {
    'prefix': {
        'doi': KnownDoiPrefix.BIORXIV_MEDRXIV
    }
}
