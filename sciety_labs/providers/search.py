from typing import Iterable, Mapping, Optional, Protocol

from sciety_labs.models.article import ArticleSearchResultItem


DEFAULT_SEARCH_RESULT_LIMIT = 100


class SearchSortBy:
    RELEVANCE = 'relevance'
    PUBLICATION_DATE = 'publication_date'


class SearchProvider(Protocol):
    def iter_search_result_item(  # pylint: disable=too-many-arguments
        self,
        query: str,
        is_evaluated_only: bool = False,
        sort_by: str = SearchSortBy.RELEVANCE,
        search_parameters: Optional[Mapping[str, str]] = None,
        items_per_page: int = DEFAULT_SEARCH_RESULT_LIMIT
    ) -> Iterable[ArticleSearchResultItem]:
        pass
