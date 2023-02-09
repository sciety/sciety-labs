import dataclasses
from typing import Mapping, NamedTuple, Optional, Sequence


class ArticleMetaData(NamedTuple):
    article_doi: str
    article_title: str
    author_name_list: Optional[Sequence[str]] = None


class ArticleStats(NamedTuple):
    evaluation_count: int = 0


@dataclasses.dataclass(frozen=True)
class ArticleMention:
    article_doi: str
    comment: Optional[str] = None
    external_reference_by_name: Mapping[str, str] = dataclasses.field(default_factory=dict)
    article_meta: Optional[ArticleMetaData] = None
    article_stats: Optional[ArticleStats] = None

    def _replace(self, **changes) -> 'ArticleMention':
        return dataclasses.replace(self, **changes)
