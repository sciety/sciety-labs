from typing import Mapping, Optional, Protocol, Sequence

from sciety_labs.providers.interfaces.article_recommendation import (
    InternalArticleFieldName,
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList
)


class AsyncSingleArticleRecommendationProvider(Protocol):
    async def get_article_recommendation_list_for_article_doi(  # pylint: disable=too-many-arguments
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None,
        filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
        fields: Optional[Sequence[InternalArticleFieldName]] = None,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleRecommendationList:
        pass
