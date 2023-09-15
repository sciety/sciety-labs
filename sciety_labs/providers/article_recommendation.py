import dataclasses
from datetime import datetime
from typing import Iterable, Optional, Protocol, Sequence

from sciety_labs.models.article import ArticleMention


@dataclasses.dataclass(frozen=True)
class ArticleRecommendation(ArticleMention):
    pass


@dataclasses.dataclass(frozen=True)
class ArticleRecommendationList:
    recommendations: Sequence[ArticleRecommendation]
    recommendation_timestamp: datetime


class ArticleRecommendationProvider(Protocol):
    def get_article_recommendation_list_for_article_dois(
        self,
        article_dois: Iterable[str],
        max_recommendations: Optional[int] = None
    ) -> ArticleRecommendationList:
        pass


class SingleArticleRecommendationProvider(Protocol):
    def get_article_recommendation_list_for_article_doi(
        self,
        article_doi: str,
        max_recommendations: Optional[int] = None
    ) -> ArticleRecommendationList:
        pass
