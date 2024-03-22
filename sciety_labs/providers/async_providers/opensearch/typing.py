from typing import Sequence
from typing_extensions import NotRequired, TypedDict


class DocumentCrossrefAuthorDict(TypedDict):
    orcid: NotRequired[str]
    family_name: NotRequired[str]
    given_name: NotRequired[str]
    sequence: NotRequired[str]
    suffix: NotRequired[str]


class DocumentCrossrefDict(TypedDict):
    title_with_markup: NotRequired[str]
    publication_date: NotRequired[str]
    author_list: NotRequired[Sequence[DocumentCrossrefAuthorDict]]


class DocumentS2AuthorDict(TypedDict):
    name: str
    s2_author_id: NotRequired[str]


class DocumentS2Dict(TypedDict):
    title: str
    author_list: NotRequired[Sequence[DocumentS2AuthorDict]]


class DocumentEuropePmcCollectiveAuthorDict(TypedDict):
    collective_name: NotRequired[str]


class DocumentEuropePmcIndividualAuthorDict(TypedDict):
    full_name: NotRequired[str]
    initials: NotRequired[str]
    last_name: NotRequired[str]
    first_name: NotRequired[str]


class DocumentEuropePmcAuthorDict(
    DocumentEuropePmcCollectiveAuthorDict,
    DocumentEuropePmcIndividualAuthorDict
):
    pass


class DocumentEuropePmcDict(TypedDict):
    title_with_markup: NotRequired[str]
    first_publication_date: NotRequired[str]
    author_list: NotRequired[Sequence[DocumentEuropePmcAuthorDict]]


class DocumentScietyDict(TypedDict):
    evaluation_count: NotRequired[int]


class DocumentDict(TypedDict):
    doi: str
    crossref: NotRequired[DocumentCrossrefDict]
    s2: NotRequired[DocumentS2Dict]
    europepmc: NotRequired[DocumentEuropePmcDict]
    sciety: NotRequired[DocumentScietyDict]