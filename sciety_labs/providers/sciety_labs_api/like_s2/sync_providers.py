from datetime import date
import logging
from typing import Mapping, Optional

from sciety_labs.models.article import iter_preprint_article_mention
from sciety_labs.providers.interfaces.article_recommendation import (
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList,
    SingleArticleRecommendationProvider
)
from sciety_labs.providers.utils.requests_provider import RequestsProvider
from sciety_labs.utils.requests import get_response_timestamp

from sciety_labs.providers.semantic_scholar.utils import (
    _iter_article_recommendation_from_recommendation_response_json
)


LOGGER = logging.getLogger(__name__)


class ScietyLabsApiSingleArticleRecommendationProvider(
    RequestsProvider,
    SingleArticleRecommendationProvider
):
    def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None,
        filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleRecommendationList:
        LOGGER.info(
            'Fetching article recommendations from Sciety Labs API for DOI: %r',
            article_doi
        )
        url = (
            'http://localhost:8000/api/like/s2/recommendations/v1/papers/forpaper/DOI:'
            + article_doi
        )
        params: dict = {
            'fields': 'externalIds,title'
        }
        if max_recommendations is not None:
            params['limit'] = max_recommendations
        if filter_parameters and filter_parameters.evaluated_only is not None:
            params['_evaluated_only'] = str(filter_parameters.evaluated_only).lower()
        if filter_parameters and filter_parameters.from_publication_date is not None:
            params['_published_within_last_n_days'] = str(
                (date.today() - filter_parameters.from_publication_date).days
            )
        response = self.requests_session.get(
            url=url,
            params=params,
            headers=self.get_headers(headers=headers)
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
