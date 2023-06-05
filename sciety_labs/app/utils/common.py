from typing import Optional

from sciety_labs.models.lists import OwnerMetaData, OwnerTypes
from sciety_labs.utils.text import remove_markup


DEFAULT_ITEMS_PER_PAGE = 10


def get_page_title(text: str) -> str:
    return remove_markup(text)


def get_owner_url(owner: OwnerMetaData) -> Optional[str]:
    if owner.owner_type == OwnerTypes.USER and owner.twitter_handle:
        return f'https://sciety.org/users/{owner.twitter_handle}'
    if owner.owner_type == OwnerTypes.GROUP and owner.slug:
        return f'https://sciety.org/groups/{owner.slug}'
    return None
