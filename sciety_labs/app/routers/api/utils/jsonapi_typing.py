from typing import Sequence
from typing_extensions import NotRequired, TypedDict


class JsonApiErrorDict(TypedDict):
    # https://jsonapi.org/format/#errors
    status: NotRequired[str]
    title: NotRequired[str]
    detail: NotRequired[str]


class JsonApiErrorsResponseDict(TypedDict):
    errors: Sequence[JsonApiErrorDict]
