from typing import Any, Mapping, Sequence
from typing_extensions import NotRequired, TypedDict


JsonMetaObjectDict = Mapping[str, Any]


class JsonApiErrorDict(TypedDict):
    # https://jsonapi.org/format/#errors
    status: NotRequired[str]
    title: NotRequired[str]
    detail: NotRequired[str]
    meta: NotRequired[JsonMetaObjectDict]


class JsonApiErrorsResponseDict(TypedDict):
    errors: Sequence[JsonApiErrorDict]
