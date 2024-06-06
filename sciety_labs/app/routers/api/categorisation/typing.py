from typing import Optional, Sequence
from typing_extensions import NotRequired, TypedDict


class JsonApiErrorDict(TypedDict):
    # https://jsonapi.org/format/#errors
    status: NotRequired[str]
    title: NotRequired[str]
    detail: NotRequired[str]


class JsonApiErrorsResponseDict(TypedDict):
    errors: Sequence[JsonApiErrorDict]


class CategorisationDict(TypedDict):
    display_name: str
    type: str
    source_id: str


class ArticleDict(TypedDict):
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
