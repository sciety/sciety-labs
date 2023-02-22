import dataclasses
import itertools
import logging
from typing import Iterable, Optional

import requests

from sciety_labs.models.article import ArticleMetaData


LOGGER = logging.getLogger(__name__)


MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS = 100


@dataclasses.dataclass(frozen=True)
class ArticleRecommendation:
    article_doi: str
    article_meta: ArticleMetaData


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
                article_title=recommended_paper_json['title']
            )
        )


class SemanticScholarProvider:
    def __init__(
        self,
        requests_session: Optional[requests.Session] = None
    ) -> None:
        self.headers: dict = {}
        if requests_session is None:
            requests_session = requests.Session()
        self.requests_session = requests_session

    def iter_article_recommendation_for_article_dois(
        self,
        article_dois: Iterable[str]
    ) -> Iterable[ArticleRecommendation]:
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
                'limit': '10'
            },
            headers=self.headers,
            timeout=5 * 60
        )
        response.raise_for_status()
        response_json = response.json()
        LOGGER.debug('Semantic Scholar, response_json=%r', response_json)
        return _iter_article_recommendation_from_recommendation_response_json(
            response_json
        )
