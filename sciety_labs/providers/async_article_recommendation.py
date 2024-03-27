from typing import Mapping, Optional, Protocol

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList
)


class AsyncSingleArticleRecommendationProvider(Protocol):
    async def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None,
        filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleRecommendationList:
        pass
