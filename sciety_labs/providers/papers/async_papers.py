import dataclasses
import logging
from typing import Mapping, Optional, Sequence

from sciety_labs.app.routers.api.papers.typing import (
    ClassificationResponseDict,
    PaperDict,
    PaperSearchResponseDict
)
from sciety_labs.models.article import ArticleMetaData, ArticleSearchResultItem
from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider
from sciety_labs.utils.datetime import parse_date_or_none


LOGGER = logging.getLogger(__name__)


DEFAULT_PROVIDER_PAPER_FIELDS = {
    'doi'
}


@dataclasses.dataclass(frozen=True)
class PageNumberBasedPaginationParameters:
    page: int
    items_per_page: int


@dataclasses.dataclass(frozen=True)
class PageNumberBasedArticleSearchResultList:
    items: Sequence[ArticleSearchResultItem]
    page: int
    total: int


def get_category_display_names_for_classification_response_dict(
    classification_response_dict: ClassificationResponseDict
) -> Sequence[str]:
    return [
        classification_dict['attributes']['display_name']
        for classification_dict in classification_response_dict['data']
    ]


def get_search_result_item_for_paper_dict(
    paper_dict: PaperDict
) -> ArticleSearchResultItem:
    LOGGER.debug('paper_dict: %r', paper_dict)
    paper_attributes_dict = paper_dict['attributes']
    doi = paper_attributes_dict['doi']
    return ArticleSearchResultItem(
        article_doi=doi,
        article_meta=ArticleMetaData(
            article_doi=doi,
            article_title=paper_attributes_dict.get('title'),
            published_date=parse_date_or_none(paper_attributes_dict.get('publication_date'))
        )
    )


def get_search_result_list_items_for_paper_search_response_dict(
    paper_search_response_dict: PaperSearchResponseDict
) -> Sequence[ArticleSearchResultItem]:
    LOGGER.debug('paper_search_response_dict: %r', paper_search_response_dict)
    return [
        get_search_result_item_for_paper_dict(paper_dict)
        for paper_dict in paper_search_response_dict['data']
    ]


def get_search_result_list_for_paper_search_response_dict(
    paper_search_response_dict: PaperSearchResponseDict
) -> PageNumberBasedArticleSearchResultList:
    meta = paper_search_response_dict.get('meta')
    assert meta
    return PageNumberBasedArticleSearchResultList(
        items=get_search_result_list_items_for_paper_search_response_dict(
            paper_search_response_dict
        ),
        page=1,
        total=meta['total']
    )


class AsyncPapersProvider(AsyncRequestsProvider):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.headers['accept'] = 'application/json'

    async def get_category_display_name_list(
        self,
        evaluated_only: bool = False,
        headers: Optional[Mapping[str, str]] = None
    ) -> Sequence[str]:
        url = 'http://localhost:8000/api/papers/v1/preprints/classifications'
        async with self.client_session.get(
            url,
            params={
                'filter[evaluated_only]': str(evaluated_only).lower()
            },
            headers=self.get_headers(headers=headers),
            timeout=self.timeout
        ) as response:
            LOGGER.info(
                'Async Response url=%r, status=%r',
                response.request_info.url,
                response.status
            )
            LOGGER.debug('response: %r', response)
            if response.status == 400:
                LOGGER.warning(
                    'Bad Request(400), url=%r, response=%r',
                    response.request_info.url,
                    await response.read()
                )
            response.raise_for_status()
            response_json: ClassificationResponseDict = await response.json()
            LOGGER.debug('Categories, response_json=%r', response_json)
            return get_category_display_names_for_classification_response_dict(
                response_json
            )

    async def get_preprints_for_category_search_results_list(
        self,
        category: str,
        pagination_parameters: PageNumberBasedPaginationParameters,
        evaluated_only: bool = False,
        headers: Optional[Mapping[str, str]] = None
    ) -> PageNumberBasedArticleSearchResultList:
        url = 'http://localhost:8000/api/papers/v1/preprints'
        async with self.client_session.get(
            url,
            params={
                'page[number]': pagination_parameters.page,
                'page[size]': pagination_parameters.items_per_page,
                'filter[category]': category,
                'filter[evaluated_only]': str(evaluated_only).lower(),
                'fields[paper]': ','.join(DEFAULT_PROVIDER_PAPER_FIELDS)
            },
            headers=self.get_headers(headers=headers),
            timeout=self.timeout
        ) as response:
            LOGGER.info(
                'Async Response url=%r, status=%r',
                response.request_info.url,
                response.status
            )
            LOGGER.debug('response: %r', response)
            if response.status == 400:
                LOGGER.warning(
                    'Bad Request(400), url=%r, response=%r',
                    response.request_info.url,
                    await response.read()
                )
            response.raise_for_status()
            response_json: PaperSearchResponseDict = await response.json()
            LOGGER.debug('Papers search, response_json=%r', response_json)
            return get_search_result_list_for_paper_search_response_dict(
                response_json
            )
