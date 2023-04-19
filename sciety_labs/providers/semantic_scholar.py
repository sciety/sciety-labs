import dataclasses
import itertools
import logging
from typing import Iterable, Optional, Sequence

import requests

from sciety_labs.models.article import ArticleMention, ArticleMetaData


LOGGER = logging.getLogger(__name__)


MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS = 100

# This is the number of recommendations we ask Semantic Scholar to generate,
# before post filtering
DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS = 500


SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID = 'semantic_scholar_paper_id'


@dataclasses.dataclass(frozen=True)
class ArticleRecommendation(ArticleMention):
    pass


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


@dataclasses.dataclass(frozen=True)
class ArticleRecommendationList:
    recommendations: Sequence[ArticleRecommendation]


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
        return ArticleRecommendationList(
            recommendations=list(_iter_article_recommendation_from_recommendation_response_json(
                response_json
            ))
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
