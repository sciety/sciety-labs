import dataclasses
from datetime import date
from typing import Iterable, Optional, Sequence

from sciety_labs.models.article import ArticleMetaData, ArticleSearchResultItem
from sciety_labs.providers.search import SearchDateRange, SearchParameters, SearchSortBy


DEFAULT_EUROPE_PMC_SEARCH_RESULT_LIMIT = 100

START_CURSOR = '*'

EUROPE_PMC_PREPRINT_SERVERS = ['bioRxiv', 'medRxiv', 'Research Square', 'SciELO Preprints']


@dataclasses.dataclass(frozen=True)
class CursorBasedArticleSearchResultList:
    items: Sequence[ArticleSearchResultItem]
    cursor: str
    total: int
    next_cursor: Optional[str]


def _iter_article_search_result_item_from_search_response_json(
    search_response_json: dict
) -> Iterable[ArticleSearchResultItem]:
    for item_json in search_response_json.get('resultList', {}).get('result', []):
        article_doi = item_json.get('doi')
        if not article_doi:  # pylint: disable=duplicate-code
            continue
        yield ArticleSearchResultItem(
            article_doi=article_doi,
            article_meta=ArticleMetaData(
                article_doi=article_doi,
                article_title=item_json['title']
            )
        )


def get_preprint_servers_query(preprint_servers: Sequence[str]) -> str:
    return ' OR '.join([
        f'PUBLISHER:"{preprint_server}"'
        for preprint_server in preprint_servers
    ])


def get_first_published_date_within_dates(
    from_date: Optional[date],
    to_date: Optional[date]
) -> str:
    if not from_date:
        return ''
    if not to_date:
        to_date = date.today()
    return f'(FIRST_PDATE:[{from_date.isoformat()} TO {to_date.isoformat()}])'


def get_query_with_additional_filters(search_parameters: SearchParameters) -> str:
    preprint_servers_query = get_preprint_servers_query(EUROPE_PMC_PREPRINT_SERVERS)
    result = f'({preprint_servers_query})'
    if search_parameters.is_evaluated_only:
        result += ' (LABS_PUBS:"2112")'
    result += ' ' + get_first_published_date_within_dates(
        SearchDateRange.get_from_date(search_parameters.date_range),
        SearchDateRange.get_to_date(search_parameters.date_range)
    )
    result += f' ({search_parameters.query})'
    if search_parameters.sort_by == SearchSortBy.PUBLICATION_DATE:
        result += ' sort_date:y'
    return result
