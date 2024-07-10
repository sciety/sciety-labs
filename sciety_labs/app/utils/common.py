from typing import Annotated, Optional

from fastapi import Depends, Request
import fastapi

from sciety_labs.models.lists import OwnerMetaData, OwnerTypes
from sciety_labs.providers.semantic_scholar.semantic_scholar import (
    DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
)
from sciety_labs.utils.pagination import UrlPaginationParameters
from sciety_labs.utils.text import remove_markup


DEFAULT_ITEMS_PER_PAGE = 10


# Note: we are aiming to include all of the recommendations in the RSS
#   because RSS clients may sort by publication date, whereas the recommendations
#   are otherwise sorted by relevancy
DEFAULT_ARTICLE_RECOMMENDATION_RSS_ITEM_COUNT = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS


ATOM_XML_PATH_SUFFIX = '/atom.xml'


def get_page_title(text: str) -> str:
    return remove_markup(text)


def get_owner_url(owner: OwnerMetaData) -> Optional[str]:
    if owner.owner_type == OwnerTypes.USER and owner.twitter_handle:
        return f'https://sciety.org/users/{owner.twitter_handle}'
    if owner.owner_type == OwnerTypes.GROUP and owner.slug:
        return f'https://sciety.org/groups/{owner.slug}'
    return None


def get_rss_url(request: Request):
    return (
        request
        .url
        .remove_query_params(['page', 'items_per_page', 'enable_pagination'])
        .replace(
            path=request.url.path + ATOM_XML_PATH_SUFFIX
        )
    )


async def get_pagination_parameters(
    items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
    page: int = 1,
    enable_pagination: bool = True
) -> UrlPaginationParameters:
    return UrlPaginationParameters(
        page=page,
        items_per_page=items_per_page,
        enable_pagination=enable_pagination
    )


AnnotatedPaginationParameters = Annotated[
    UrlPaginationParameters, Depends(get_pagination_parameters)
]


async def get_from_sciety_parameter(
    from_sciety: bool = False,
    from_sciety_alias: bool = fastapi.Query(False, alias='from-sciety'),
) -> bool:
    return from_sciety or from_sciety_alias


AnnotatedFromScietyParameter = Annotated[
    bool,
    Depends(get_from_sciety_parameter)
]
