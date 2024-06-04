from typing import Sequence
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
    categorisation: NotRequired[Sequence[CategorisationDict]]


class CategorisationResponseDict(TypedDict):
    data: NotRequired[Sequence[CategorisationDict]]


class ArticleResponseDict(TypedDict):
    data: ArticleDict


class ArticleSearchResponseDict(TypedDict):
    data: Sequence[ArticleDict]
