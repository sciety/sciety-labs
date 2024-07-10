import itertools
import logging
from datetime import date, datetime
import os
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

import requests
from requests_cache import CachedResponse

from sciety_labs.models.article import (
    ArticleMetaData,
    ArticleSearchResultItem,
    iter_preprint_article_mention
)
from sciety_labs.providers.interfaces.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationList,
    ArticleRecommendationProvider
)
from sciety_labs.providers.requests_provider import RequestsProvider
from sciety_labs.providers.semantic_scholar.utils import (
    MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS,
    SEMANTIC_SCHOLAR_API_KEY_FILE_PATH_ENV_VAR
)
from sciety_labs.utils.datetime import get_utc_timestamp_with_tzinfo, get_utcnow, parse_date_or_none


LOGGER = logging.getLogger(__name__)


MAX_SEMANTIC_SCHOLAR_SEARCH_ITEMS = 100
MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT = 9999
MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET = MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT - 1


# This is the number of recommendations we ask Semantic Scholar to generate,
# before post filtering
DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS = 500

DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT = 100


SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID = 'semantic_scholar_paper_id'


SEMANTIC_SCHOLAR_REQUESTED_FIELDS = [
    'externalIds',
    'url',
    'title',
    'abstract',
    'authors',
    'publicationDate'
]

SEMANTIC_SCHOLAR_SEARCH_VENUES = ['bioRxiv', 'medRxiv', 'Research Square']

SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITHOUT_VENUES: dict = {'year': 2023}
SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITH_VENUES: dict = {
    **SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITHOUT_VENUES,
    'venue': ','.join(SEMANTIC_SCHOLAR_SEARCH_VENUES)
}


def _get_recommendation_request_payload_for_paper_ids_or_external_ids(
    paper_ids_or_external_ids: Iterable[str]
) -> dict:
    return {
        'positivePaperIds': list(itertools.islice(
            paper_ids_or_external_ids,
            MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS
        )),
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


def _get_article_meta_from_paper_json(
    paper_json: dict
) -> ArticleMetaData:
    article_doi = paper_json.get('externalIds', {}).get('DOI')
    assert article_doi
    return ArticleMetaData(
        article_doi=article_doi,
        article_title=paper_json['title'],
        published_date=parse_date_or_none(paper_json.get('publicationDate')),
        author_name_list=_get_author_names_from_recommended_paper_json(
            paper_json
        )
    )


def _iter_article_recommendation_from_recommendation_response_json(
    recommendation_response_json: dict
) -> Iterable[ArticleRecommendation]:
    for recommended_paper_json in recommendation_response_json['recommendedPapers']:
        article_doi = recommended_paper_json.get('externalIds', {}).get('DOI')
        if not article_doi:
            continue
        yield ArticleRecommendation(
            article_doi=article_doi,
            article_meta=_get_article_meta_from_paper_json(recommended_paper_json),
            external_reference_by_name={
                SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: recommended_paper_json.get('paperId')
            }
        )


def iter_article_search_result_item_from_search_response_json(
    search_response_json: dict
) -> Iterable[ArticleSearchResultItem]:
    for item_json in search_response_json.get('data', []):
        article_doi = item_json.get('externalIds', {}).get('DOI')
        if not article_doi:
            continue
        yield ArticleSearchResultItem(
            article_doi=article_doi,
            article_meta=_get_article_meta_from_paper_json(item_json),
            external_reference_by_name={
                SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: item_json.get('paperId')
            }
        )


def get_response_timestamp(response: requests.Response) -> datetime:
    if isinstance(response, CachedResponse):
        return get_utc_timestamp_with_tzinfo(response.created_at)
    return get_utcnow()


class SemanticScholarProvider(RequestsProvider, ArticleRecommendationProvider):
    def __init__(
        self,
        api_key_file_path: Optional[str],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        if api_key_file_path:
            api_key = Path(api_key_file_path).read_text(encoding='utf-8')
            self.headers['x-api-key'] = api_key

    def iter_paper_ids_or_external_ids_for_article_dois(
        self,
        article_dois: Sequence[str]
    ) -> Iterable[str]:
        for doi in article_dois:
            yield f'DOI:{doi}'

    def get_article_recommendation_list_for_article_dois(
        self,
        article_dois: Iterable[str],
        max_recommendations: Optional[int] = None
    ) -> ArticleRecommendationList:
        if not max_recommendations:
            max_recommendations = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
        request_json = _get_recommendation_request_payload_for_paper_ids_or_external_ids(
            paper_ids_or_external_ids=self.iter_paper_ids_or_external_ids_for_article_dois(
                article_dois=list(itertools.islice(
                    article_dois,
                    MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS
                ))
            )
        )
        LOGGER.info('Semantic Scholar, request_json=%r', request_json)
        response = self.requests_session.post(
            'https://api.semanticscholar.org/recommendations/v1/papers/',
            json=request_json,
            params={
                'fields': ','.join(SEMANTIC_SCHOLAR_REQUESTED_FIELDS),
                'limit': str(max_recommendations)
            },
            headers=self.headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        response_json = response.json()
        LOGGER.debug('Semantic Scholar, response_json=%r', response_json)
        recommendation_timestamp = get_response_timestamp(response)
        return ArticleRecommendationList(
            recommendations=list(iter_preprint_article_mention(
                _iter_article_recommendation_from_recommendation_response_json(
                    response_json
                )
            )),
            recommendation_timestamp=recommendation_timestamp
        )


def get_year_request_parameter_for_date_range(
    from_date: date,
    to_date: date
) -> str:
    from_year = from_date.year
    to_year = to_date.year
    if to_year == from_year:
        return str(from_year)
    return f'{from_year}-{to_year}'


class SemanticScholarTitleAbstractEmbeddingVectorProvider(RequestsProvider):
    def get_embedding_vector(
        self,
        title: str,
        abstract: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> Sequence[float]:
        paper_id = '_dummy_paper_id'
        papers = [{
            'paper_id': paper_id,
            'title': title,
            'abstract': abstract
        }]
        response = requests.post(
            'https://model-apis.semanticscholar.org/specter/v1/invoke',
            json=papers,
            timeout=self.timeout,
            headers=self.get_headers(headers=headers)
        )
        response.raise_for_status()
        embeddings_by_paper_id = {
            pred['paper_id']: pred['embedding']
            for pred in response.json().get('preds')
        }
        return embeddings_by_paper_id[paper_id]


def get_semantic_scholar_api_key_file_path() -> Optional[str]:
    return os.getenv(SEMANTIC_SCHOLAR_API_KEY_FILE_PATH_ENV_VAR)


def get_semantic_scholar_provider(
    **kwargs
) -> Optional[SemanticScholarProvider]:
    api_key_file_path = get_semantic_scholar_api_key_file_path()
    if api_key_file_path and not os.path.exists(api_key_file_path):
        LOGGER.info(
            'Semantic Scholar API key file does not exist, not using api key: %r',
            api_key_file_path
        )
        api_key_file_path = None
    LOGGER.info('Semantic Scholar API key: %r', api_key_file_path)
    return SemanticScholarProvider(api_key_file_path, **kwargs)
