from typing import Sequence
from typing_extensions import NotRequired, TypedDict


class CategorisationDict(TypedDict):
    display_name: str
    source_id: str


class CategorisationResponseDict(TypedDict):
    categories: NotRequired[Sequence[CategorisationDict]]
