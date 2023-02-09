import dataclasses
from typing import Mapping, NamedTuple, Optional, Sequence


class ArticleMetaData(NamedTuple):
    article_doi: str
    article_title: str
    author_name_list: Optional[Sequence[str]] = None


@dataclasses.dataclass(frozen=True)
class ArticleMention:
    article_doi: str
    comment: Optional[str] = None
    external_source_ids_by_name: Mapping[str, str] = dataclasses.field(default_factory=dict)
    article_meta: Optional[ArticleMetaData] = None

    def _replace(self, **changes) -> 'ArticleMention':
        return dataclasses.replace(self, **changes)
