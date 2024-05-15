from typing import Sequence
from typing_extensions import NotRequired, TypedDict


class CategorisationDict(TypedDict):
    categories: NotRequired[Sequence[str]]
