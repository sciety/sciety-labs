import dataclasses
from typing import Optional, Sequence

from sciety_labs.models.article import ArticleSearchResultItem


SEMANTIC_SCHOLAR_API_KEY_FILE_PATH_ENV_VAR = 'SEMANTIC_SCHOLAR_API_KEY_FILE_PATH'

MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS = 100


@dataclasses.dataclass(frozen=True)
class ArticleSearchResultList:
    items: Sequence[ArticleSearchResultItem]
    offset: int
    total: int
    next_offset: Optional[int] = None
