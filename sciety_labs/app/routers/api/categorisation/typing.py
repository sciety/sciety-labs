from typing import Sequence
from typing_extensions import NotRequired, TypedDict


class CategorisationResponseDict(TypedDict):
    categories: NotRequired[Sequence[str]]
