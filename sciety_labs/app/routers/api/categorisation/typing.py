from typing import Literal, Optional, Sequence
from typing_extensions import NotRequired, TypedDict


class CategorisationDict(TypedDict):
    display_name: str
    type: str
    source_id: str


class ArticleDict(TypedDict):
    type: str
    doi: str
    title: NotRequired[Optional[str]]
    publication_date: NotRequired[Optional[str]]
    evaluation_count: NotRequired[Optional[int]]
    latest_evaluation_activity_timestamp: NotRequired[Optional[str]]
    categorisation: NotRequired[Sequence[CategorisationDict]]


class CategorisationResponseDict(TypedDict):
    data: NotRequired[Sequence[CategorisationDict]]


class ArticleResponseDict(TypedDict):
    data: ArticleDict


class ArticleSearchMetaDict(TypedDict):
    total: NotRequired[int]


class ArticleSearchResponseDict(TypedDict):
    data: Sequence[ArticleDict]
    meta: NotRequired[ArticleSearchMetaDict]
