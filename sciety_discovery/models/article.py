from typing import NamedTuple, Optional


class ArticleMetaData(NamedTuple):
    article_doi: str
    article_title: str


class ArticleMention(NamedTuple):
    article_doi: str
    comment: Optional[str] = None
    article_meta: Optional[ArticleMetaData] = None
