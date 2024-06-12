from typing import Optional, Sequence
from typing_extensions import NotRequired, TypedDict


class CategorisationAttributesDict(TypedDict):
    display_name: str
    source_id: str


class CategorisationDict(TypedDict):
    type: str
    id: str
    attributes: CategorisationAttributesDict


class PaperAttributesDict(TypedDict):
    doi: str
    title: NotRequired[Optional[str]]
    publication_date: NotRequired[Optional[str]]
    evaluation_count: NotRequired[Optional[int]]
    has_evaluations: NotRequired[Optional[bool]]
    latest_evaluation_activity_timestamp: NotRequired[Optional[str]]
    classifications: NotRequired[Sequence[CategorisationDict]]


class PaperDict(TypedDict):
    type: str
    id: str
    attributes: PaperAttributesDict


class CategorisationResponseDict(TypedDict):
    data: NotRequired[Sequence[CategorisationDict]]


class PaperResponseDict(TypedDict):
    data: PaperDict


class PaperSearchMetaDict(TypedDict):
    total: NotRequired[int]


class PaperSearchResponseDict(TypedDict):
    data: Sequence[PaperDict]
    meta: NotRequired[PaperSearchMetaDict]
