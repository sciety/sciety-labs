import dataclasses
from datetime import datetime
from typing import Sequence

from sciety_labs.models.article import ArticleMention


@dataclasses.dataclass(frozen=True)
class ArticleRecommendation(ArticleMention):
    pass


@dataclasses.dataclass(frozen=True)
class ArticleRecommendationList:
    recommendations: Sequence[ArticleRecommendation]
    recommendation_timestamp: datetime
