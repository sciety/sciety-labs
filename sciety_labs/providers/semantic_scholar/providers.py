import itertools
import logging
from datetime import datetime
import os
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

import requests
from requests_cache import CachedResponse

from sciety_labs.models.article import (
    iter_preprint_article_mention
)
from sciety_labs.providers.interfaces.article_recommendation import (
    ArticleRecommendationList,
    ArticleRecommendationProvider
)
from sciety_labs.providers.requests_provider import RequestsProvider
from sciety_labs.providers.semantic_scholar.utils import (
    DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS,
    MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS,
    SEMANTIC_SCHOLAR_REQUESTED_FIELDS,
    _get_recommendation_request_payload_for_paper_ids_or_external_ids,
    _iter_article_recommendation_from_recommendation_response_json,
    get_semantic_scholar_api_key_file_path
)
from sciety_labs.utils.datetime import get_utc_timestamp_with_tzinfo, get_utcnow


LOGGER = logging.getLogger(__name__)


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
