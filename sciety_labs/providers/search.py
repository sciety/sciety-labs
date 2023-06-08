from datetime import date, timedelta
from typing import Iterable, Mapping, Optional, Protocol

from attr import dataclass

from sciety_labs.models.article import ArticleSearchResultItem


DEFAULT_SEARCH_RESULT_LIMIT = 100


class SearchSortBy:
    RELEVANCE = 'relevance'
    PUBLICATION_DATE = 'publication_date'


class SearchDateRange:
    LAST_30_DAYS = '30d'
    LAST_90_DAYS = '90d'
    THIS_YEAR = 'this_year'
    SINCE_2022 = 'since_2022'
    SINCE_2021 = 'since_2021'

    @staticmethod
    def is_valid(date_range: str) -> bool:
        return date_range in {
            SearchDateRange.LAST_30_DAYS,
            SearchDateRange.LAST_90_DAYS,
            SearchDateRange.THIS_YEAR,
            SearchDateRange.SINCE_2022,
            SearchDateRange.SINCE_2021
        }

    @staticmethod
    def assert_valid(date_range: str):
        if not SearchDateRange.is_valid(date_range):
            raise ValueError(f'invalid date range: {date_range}')

    @staticmethod
    def get_from_date(date_range: str) -> date:
        SearchDateRange.assert_valid(date_range)
        today = date.today()
        if date_range == SearchDateRange.LAST_30_DAYS:
            return today - timedelta(days=30)
        if date_range == SearchDateRange.LAST_90_DAYS:
            return today - timedelta(days=90)
        if date_range == SearchDateRange.THIS_YEAR:
            return date(today.year, 1, 1)
        if date_range == SearchDateRange.SINCE_2022:
            return date(2022, 1, 1)
        if date_range == SearchDateRange.SINCE_2021:
            return date(2021, 1, 1)
        raise ValueError(f'invalid date range: {date_range}')

    @staticmethod
    def get_to_date(date_range: str) -> date:
        SearchDateRange.assert_valid(date_range)
        return date.today()


@dataclass
class SearchParameters:
    query: str
    is_evaluated_only: bool = False
    sort_by: str = SearchSortBy.RELEVANCE
    date_range: str = SearchDateRange.LAST_30_DAYS
    additional_search_parameters: Optional[Mapping[str, str]] = None
    items_per_page: int = DEFAULT_SEARCH_RESULT_LIMIT


class SearchProvider(Protocol):
    def iter_search_result_item(  # pylint: disable=too-many-arguments
        self,
        search_parameters: SearchParameters
    ) -> Iterable[ArticleSearchResultItem]:
        pass
