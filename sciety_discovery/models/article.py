from typing import NamedTuple, Optional, Sequence


class ArticleMetaData(NamedTuple):
    article_doi: str
    article_title: str
    author_name_list: Optional[Sequence[str]] = None


class ArticleMention(NamedTuple):
    article_doi: str
    comment: Optional[str] = None
    article_meta: Optional[ArticleMetaData] = None
