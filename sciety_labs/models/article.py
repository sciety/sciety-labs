import dataclasses
from datetime import datetime
from typing import Mapping, NamedTuple, Optional, Sequence


DOI_ARTICLE_ID_PREFIX = 'doi:'


def is_doi_article_id(article_id: str) -> bool:
    return article_id.startswith(DOI_ARTICLE_ID_PREFIX)


def get_doi_from_article_id_or_none(article_id: str) -> Optional[str]:
    if not is_doi_article_id(article_id):
        return None
    return article_id[len(DOI_ARTICLE_ID_PREFIX):]


class ArticleMetaData(NamedTuple):
    article_doi: str
    article_title: str
    author_name_list: Optional[Sequence[str]] = None


class ArticleStats(NamedTuple):
    evaluation_count: int = 0


@dataclasses.dataclass(frozen=True)
class ArticleMention:
    article_doi: str
    created_at_timestamp: Optional[datetime] = None
    comment: Optional[str] = None
    external_reference_by_name: Mapping[str, str] = dataclasses.field(default_factory=dict)
    article_meta: Optional[ArticleMetaData] = None
    article_stats: Optional[ArticleStats] = None

    def _replace(self, **changes) -> 'ArticleMention':
        return dataclasses.replace(self, **changes)

    def get_created_at_sort_key(self) -> datetime:
        assert self.created_at_timestamp
        return self.created_at_timestamp

    @property
    def created_at_isoformat(self) -> Optional[str]:
        if not self.created_at_timestamp:
            return None
        return self.created_at_timestamp.strftime(r'%Y-%m-%d')

    @property
    def created_at_display_format(self) -> Optional[str]:
        if not self.created_at_timestamp:
            return None
        return self.created_at_timestamp.strftime(r'%b %-d, %Y')
