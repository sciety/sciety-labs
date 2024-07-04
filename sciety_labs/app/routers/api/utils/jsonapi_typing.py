from typing import Any, Mapping, Sequence
from typing_extensions import NotRequired, TypedDict


JsonMetaObjectDict = Mapping[str, Any]


class JsonApiErrorSourceDict(TypedDict):
    parameter: NotRequired[str]


class JsonApiErrorDict(TypedDict):
    # https://jsonapi.org/format/#errors
    status: NotRequired[str]
    title: NotRequired[str]
    detail: NotRequired[str]
    source: NotRequired[JsonApiErrorSourceDict]
    meta: NotRequired[JsonMetaObjectDict]


class JsonApiErrorsResponseDict(TypedDict):
    errors: Sequence[JsonApiErrorDict]
