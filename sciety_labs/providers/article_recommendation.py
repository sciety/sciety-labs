import dataclasses
from datetime import date, datetime
from typing import Iterable, Mapping, Optional, Protocol, Sequence, Set

from sciety_labs.models.article import ArticleMention


@dataclasses.dataclass(frozen=True)
class ArticleRecommendation(ArticleMention):
    score: Optional[float] = None


@dataclasses.dataclass(frozen=True)
class ArticleRecommendationFilterParameters:
    from_publication_date: Optional[date] = None
    evaluated_only: bool = False
    exclude_article_dois: Optional[Set[str]] = None


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
        max_recommendations: Optional[int] = None,
        filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleRecommendationList:
        pass
