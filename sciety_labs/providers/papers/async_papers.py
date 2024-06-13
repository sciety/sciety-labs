import dataclasses
import logging
from typing import Mapping, Optional, Sequence

from sciety_labs.app.routers.api.papers.typing import (
    PaperDict,
    PaperSearchResponseDict
)
from sciety_labs.models.article import ArticleMetaData, ArticleSearchResultItem
from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider


LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class PageNumberBasedArticleSearchResultList:
    items: Sequence[ArticleSearchResultItem]
    page: int


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
            article_title=paper_attributes_dict.get('title')
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
    return PageNumberBasedArticleSearchResultList(
        items=get_search_result_list_items_for_paper_search_response_dict(
            paper_search_response_dict
        ),
        page=1
    )


class AsyncPapersProvider(AsyncRequestsProvider):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.headers['accept'] = 'application/json'

    async def get_preprints_for_category_search_results_list(
        self,
        category: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> PageNumberBasedArticleSearchResultList:
        url = 'http://localhost:8000/api/papers/v1/preprints'
        async with self.client_session.get(
            url,
            params={'filter[category]': category, 'fields[paper]': 'doi,title'},
            headers=self.get_headers(headers=headers),
            timeout=self.timeout
        ) as response:
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
