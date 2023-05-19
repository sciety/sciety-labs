import dataclasses
import itertools
import logging
from datetime import datetime
from typing import Iterable, Mapping, Optional, Sequence

import requests
from requests_cache import CachedResponse

from sciety_labs.models.article import ArticleMention, ArticleMetaData, ArticleSearchResultItem
from sciety_labs.utils.datetime import get_utc_timestamp_with_tzinfo, get_utcnow


LOGGER = logging.getLogger(__name__)


MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS = 100

MAX_SEMANTIC_SCHOLAR_SEARCH_ITEMS = 100
MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT = 9999
MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET = MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT - 1


# This is the number of recommendations we ask Semantic Scholar to generate,
# before post filtering
DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS = 500

DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT = 100


SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID = 'semantic_scholar_paper_id'


@dataclasses.dataclass(frozen=True)
class ArticleRecommendation(ArticleMention):
    pass


@dataclasses.dataclass(frozen=True)
class ArticleRecommendationList:
    recommendations: Sequence[ArticleRecommendation]
    recommendation_timestamp: datetime


@dataclasses.dataclass(frozen=True)
class ArticleSearchResultList:
    items: Sequence[ArticleSearchResultItem]
    offset: int
    total: int
    next_offset: Optional[int]


def _get_recommendation_request_payload_for_article_dois(
    article_dois: Iterable[str]
) -> dict:
    return {
        'positivePaperIds': [
            f'DOI:{doi}'
            for doi in itertools.islice(
                article_dois,
                MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS
            )
        ],
        'negativePaperIds': []
    }


def _get_author_names_from_author_list_json(
    author_list_json: Sequence[dict]
) -> Sequence[str]:
    return [author['name'] for author in author_list_json]


def _get_author_names_from_recommended_paper_json(
    recommended_paper_json: dict
) -> Optional[Sequence[str]]:
    author_list_json = recommended_paper_json.get('authors')
    if not author_list_json:
        return None
    return _get_author_names_from_author_list_json(author_list_json)


def _iter_article_recommendation_from_recommendation_response_json(
    recommendation_response_json: dict
) -> Iterable[ArticleRecommendation]:
    for recommended_paper_json in recommendation_response_json['recommendedPapers']:
        article_doi = recommended_paper_json.get('externalIds', {}).get('DOI')
        if not article_doi:
            continue
        yield ArticleRecommendation(
            article_doi=article_doi,
            article_meta=ArticleMetaData(
                article_doi=article_doi,
                article_title=recommended_paper_json['title'],
                author_name_list=_get_author_names_from_recommended_paper_json(
                    recommended_paper_json
                )
            ),
            external_reference_by_name={
                SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: recommended_paper_json.get('paperId')
            }
        )


def _iter_article_search_result_item_from_search_response_json(
    search_response_json: dict
) -> Iterable[ArticleSearchResultItem]:
    for item_json in search_response_json.get('data', []):
        article_doi = item_json.get('externalIds', {}).get('DOI')
        if not article_doi:
            continue
        yield ArticleSearchResultItem(
            article_doi=article_doi,
            article_meta=ArticleMetaData(
                article_doi=article_doi,
                article_title=item_json['title'],
                author_name_list=_get_author_names_from_recommended_paper_json(
                    item_json
                )
            ),
            external_reference_by_name={
                SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: item_json.get('paperId')
            }
        )


def get_response_timestamp(response: requests.Response) -> datetime:
    if isinstance(response, CachedResponse):
        return get_utc_timestamp_with_tzinfo(response.created_at)
    return get_utcnow()


class SemanticScholarProvider:
    def __init__(
        self,
        requests_session: Optional[requests.Session] = None
    ) -> None:
        self.headers: dict = {}
        if requests_session is None:
            requests_session = requests.Session()
        self.requests_session = requests_session

    def get_article_recommendation_list_for_article_dois(
        self,
        article_dois: Iterable[str],
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
    ) -> ArticleRecommendationList:
        request_json = _get_recommendation_request_payload_for_article_dois(
            article_dois=article_dois
        )
        LOGGER.info('Semantic Scholar, request_json=%r', request_json)
        response = self.requests_session.post(
            'https://api.semanticscholar.org/recommendations/v1/papers/',
            json=request_json,
            params={
                'fields': ','.join([
                    'externalIds',
                    'url',
                    'title',
                    'abstract',
                    'authors'
                ]),
                'limit': str(max_recommendations)
            },
            headers=self.headers,
            timeout=5 * 60
        )
        response.raise_for_status()
        response_json = response.json()
        LOGGER.debug('Semantic Scholar, response_json=%r', response_json)
        recommendation_timestamp = get_response_timestamp(response)
        return ArticleRecommendationList(
            recommendations=list(_iter_article_recommendation_from_recommendation_response_json(
                response_json
            )),
            recommendation_timestamp=recommendation_timestamp
        )

    def iter_article_recommendation_for_article_dois(
        self,
        article_dois: Iterable[str],
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
    ) -> Iterable[ArticleRecommendation]:
        return self.get_article_recommendation_list_for_article_dois(
            article_dois=article_dois,
            max_recommendations=max_recommendations
        ).recommendations

    def get_search_result_list(
        self,
        query: str,
        search_parameters: Optional[Mapping[str, str]] = None,
        offset: int = 0,
        limit: int = DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT
    ) -> ArticleSearchResultList:
        request_params = {
            **(search_parameters if search_parameters else {}),
            'query': query,
            'fields': ','.join([
                'externalIds',
                'url',
                'title',
                'abstract',
                'authors'
            ]),
            'offset': str(offset),
            'limit': str(limit)
        }
        LOGGER.info('Semantic Scholar search, request_params=%r', request_params)
        response = self.requests_session.get(
            'https://api.semanticscholar.org/graph/v1/paper/search',
            params=request_params,
            headers=self.headers,
            timeout=5 * 60
        )
        LOGGER.info('Semantic Scholar search, url=%r', response.request.url)
        response.raise_for_status()
        response_json = response.json()
        LOGGER.debug('Semantic Scholar search, response_json=%r', response_json)
        return ArticleSearchResultList(
            items=list(_iter_article_search_result_item_from_search_response_json(
                response_json
            )),
            offset=response_json['offset'],
            total=response_json['total'],
            next_offset=response_json.get('next')
        )

    def iter_search_result_item(
        self,
        query: str,
        search_parameters: Optional[Mapping[str, str]] = None,
        items_per_page: int = DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT
    ) -> Iterable[ArticleSearchResultItem]:
        offset = 0
        while True:
            search_result_list = self.get_search_result_list(
                query=query,
                search_parameters=search_parameters,
                offset=offset,
                limit=items_per_page
            )
            LOGGER.info('Semantic Scholar search, total=%r', search_result_list.total)
            yield from search_result_list.items
            if not search_result_list.next_offset:
                LOGGER.info('no more search results (no next offset)')
                break
            offset = search_result_list.next_offset
            if offset > MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET:
                LOGGER.info('reached max offset')
                break
            items_per_page = min(
                items_per_page,
                MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT - offset
            )
