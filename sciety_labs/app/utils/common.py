from typing import Optional

from sciety_labs.models.lists import OwnerMetaData, OwnerTypes
from sciety_labs.providers.semantic_scholar import DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
from sciety_labs.utils.text import remove_markup


DEFAULT_ITEMS_PER_PAGE = 10


# Note: we are aiming to include all of the recommendations in the RSS
#   because RSS clients may sort by publication date, whereas the recommendations
#   are otherwise sorted by relevancy
DEFAULT_ARTICLE_RECOMMENDATION_RSS_ITEM_COUNT = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS


def get_page_title(text: str) -> str:
    return remove_markup(text)


def get_owner_url(owner: OwnerMetaData) -> Optional[str]:
    if owner.owner_type == OwnerTypes.USER and owner.twitter_handle:
        return f'https://sciety.org/users/{owner.twitter_handle}'
    if owner.owner_type == OwnerTypes.GROUP and owner.slug:
        return f'https://sciety.org/groups/{owner.slug}'
    return None
