from typing import Iterable, Mapping, NamedTuple, Optional, Protocol

from sciety_labs.models.article import ArticleSearchResultItem


DEFAULT_SEARCH_RESULT_LIMIT = 100


class SearchSortBy:
    RELEVANCE = 'relevance'
    PUBLICATION_DATE = 'publication_date'


class SearchDateRange:
    LAST_30_DAYS = '30d'
    LAST_90_DAYS = '90d'
    THIS_YEAR = 'this_year'


class SearchParameters(NamedTuple):
    query: str
    is_evaluated_only: bool = False
    sort_by: str = SearchSortBy.RELEVANCE
    additional_search_parameters: Optional[Mapping[str, str]] = None
    items_per_page: int = DEFAULT_SEARCH_RESULT_LIMIT


class SearchProvider(Protocol):
    def iter_search_result_item(  # pylint: disable=too-many-arguments
        self,
        search_parameters: SearchParameters
    ) -> Iterable[ArticleSearchResultItem]:
        pass
