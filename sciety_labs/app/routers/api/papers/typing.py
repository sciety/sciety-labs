from typing import Optional, Sequence
from typing_extensions import NotRequired, TypedDict


class ClassificationAttributesDict(TypedDict):
    display_name: str
    source_id: str


class ClassificationDict(TypedDict):
    type: str
    id: str
    attributes: ClassificationAttributesDict


class PaperAttributesDict(TypedDict):
    doi: str
    title: NotRequired[Optional[str]]
    publication_date: NotRequired[Optional[str]]
    evaluation_count: NotRequired[Optional[int]]
    has_evaluations: NotRequired[Optional[bool]]
    latest_evaluation_activity_timestamp: NotRequired[Optional[str]]
    classifications: NotRequired[Sequence[ClassificationDict]]


class PaperDict(TypedDict):
    type: str
    id: str
    attributes: PaperAttributesDict


class ClassificationResponseDict(TypedDict):
    data: NotRequired[Sequence[ClassificationDict]]


class PaperResponseDict(TypedDict):
    data: PaperDict


class PaperSearchMetaDict(TypedDict):
    total: NotRequired[int]


class PaperSearchResponseDict(TypedDict):
    data: Sequence[PaperDict]
    meta: NotRequired[PaperSearchMetaDict]
