import dataclasses
from datetime import date
import itertools
import os
from typing import Iterable, Optional, Sequence

from sciety_labs.models.article import ArticleMetaData, ArticleSearchResultItem
from sciety_labs.providers.interfaces.article_recommendation import ArticleRecommendation
from sciety_labs.utils.datetime import parse_date_or_none


SEMANTIC_SCHOLAR_API_KEY_FILE_PATH_ENV_VAR = 'SEMANTIC_SCHOLAR_API_KEY_FILE_PATH'

MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS = 100

MAX_SEMANTIC_SCHOLAR_SEARCH_ITEMS = 100
MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT = 9999
MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET = MAX_SEMANTIC_SCHOLAR_SEARCH_OFFSET_PLUS_LIMIT - 1

# This is the number of recommendations we ask Semantic Scholar to generate,
# before post filtering
DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS = 500

DEFAULT_SEMANTIC_SCHOLAR_SEARCH_RESULT_LIMIT = 100

SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID = 'semantic_scholar_paper_id'

SEMANTIC_SCHOLAR_REQUESTED_FIELDS = [
    'externalIds',
    'url',
    'title',
    'abstract',
    'authors',
    'publicationDate'
]

SEMANTIC_SCHOLAR_SEARCH_VENUES = ['bioRxiv', 'medRxiv', 'Research Square']

SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITHOUT_VENUES: dict = {'year': 2023}

SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITH_VENUES: dict = {
    **SEMANTIC_SCHOLAR_SEARCH_PARAMETERS_WITHOUT_VENUES,
    'venue': ','.join(SEMANTIC_SCHOLAR_SEARCH_VENUES)
}


@dataclasses.dataclass(frozen=True)
class ArticleSearchResultList:
    items: Sequence[ArticleSearchResultItem]
    offset: int
    total: int
    next_offset: Optional[int] = None


def _get_recommendation_request_payload_for_paper_ids_or_external_ids(
    paper_ids_or_external_ids: Iterable[str]
) -> dict:
    return {
        'positivePaperIds': list(itertools.islice(
            paper_ids_or_external_ids,
            MAX_SEMANTIC_SCHOLAR_RECOMMENDATION_REQUEST_PAPER_IDS
        )),
        'negativePaperIds': []
    }


def _get_author_names_from_author_list_json(
    author_list_json: Sequence[dict]
) -> Sequence[str]:
    return [author['name'] for author in author_list_json]


def _get_author_names_from_recommended_paper_json(
    recommended_paper_json: dict
) -> Optional[Sequence[str]]:
    author_list_json = recommended_paper_json.get('authors')
    if not author_list_json:
        return None
    return _get_author_names_from_author_list_json(author_list_json)


def _get_article_meta_from_paper_json(
    paper_json: dict
) -> ArticleMetaData:
    article_doi = paper_json.get('externalIds', {}).get('DOI')
    assert article_doi
    return ArticleMetaData(
        article_doi=article_doi,
        article_title=paper_json['title'],
        published_date=parse_date_or_none(paper_json.get('publicationDate')),
        author_name_list=_get_author_names_from_recommended_paper_json(
            paper_json
        )
    )


def _iter_article_recommendation_from_recommendation_response_json(
    recommendation_response_json: dict
) -> Iterable[ArticleRecommendation]:
    for recommended_paper_json in recommendation_response_json['recommendedPapers']:
        article_doi = recommended_paper_json.get('externalIds', {}).get('DOI')
        if not article_doi:
            continue
        yield ArticleRecommendation(
            article_doi=article_doi,
            article_meta=_get_article_meta_from_paper_json(recommended_paper_json),
            external_reference_by_name={
                SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: recommended_paper_json.get('paperId')
            }
        )


def iter_article_search_result_item_from_search_response_json(
    search_response_json: dict
) -> Iterable[ArticleSearchResultItem]:
    for item_json in search_response_json.get('data', []):
        article_doi = item_json.get('externalIds', {}).get('DOI')
        if not article_doi:
            continue
        yield ArticleSearchResultItem(
            article_doi=article_doi,
            article_meta=_get_article_meta_from_paper_json(item_json),
            external_reference_by_name={
                SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: item_json.get('paperId')
            }
        )


def get_year_request_parameter_for_date_range(
    from_date: date,
    to_date: date
) -> str:
    from_year = from_date.year
    to_year = to_date.year
    if to_year == from_year:
        return str(from_year)
    return f'{from_year}-{to_year}'


def get_semantic_scholar_api_key_file_path() -> Optional[str]:
    return os.getenv(SEMANTIC_SCHOLAR_API_KEY_FILE_PATH_ENV_VAR)
