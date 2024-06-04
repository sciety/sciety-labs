from typing import Sequence
from typing_extensions import TypedDict


class OpenSearchSearchResultHitDict(TypedDict):
    _index: str
    _id: str
    _score: float
    _source: dict


class OpenSearchSearchResultHitsDict(TypedDict):
    hits: Sequence[dict]


class OpenSearchSearchResultDict(TypedDict):
    hits: OpenSearchSearchResultHitsDict
