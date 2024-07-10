import logging
from typing import AsyncIterable, AsyncIterator, Mapping, Optional, Sequence

import aiohttp

from sciety_labs.models.article import ArticleMention, ArticleMetaData
from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider
from sciety_labs.providers.crossref.crossref import (
    get_article_meta_by_doi_map_for_response_dict_mapping,
    get_article_metadata_from_crossref_metadata,
    get_batch_doi_request_parameters,
    get_response_dict_by_doi_map,
    iter_article_mention_with_replaced_article_meta
)
from sciety_labs.utils.async_utils import get_list_for_async_iterable


LOGGER = logging.getLogger(__name__)


class AsyncCrossrefMetaDataProvider(AsyncRequestsProvider):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.headers['accept'] = 'application/json'

    async def get_crossref_metadata_dict_by_doi(
        self,
        doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> dict:
        url = f'https://api.crossref.org/works/{doi}'
        async with self.client_session.get(
            url,
            headers=self.get_headers(headers=headers),
            timeout=self.timeout
        ) as response:
            response.raise_for_status()
            response_json = await response.json()
            return response_json['message']

    async def get_article_metadata_by_doi(
        self,
        doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleMetaData:
        return get_article_metadata_from_crossref_metadata(
            doi,
            await self.get_crossref_metadata_dict_by_doi(doi, headers=headers),
        )

    async def get_batch_crossref_metadata_dict_by_doi(
        self,
        dois: Sequence[str]
    ) -> Mapping[str, dict]:
        url = 'https://api.crossref.org/works'
        params = get_batch_doi_request_parameters(dois)
        async with self.get(
            url,
            params=params,
            headers=self.get_headers(),
            timeout=self.timeout
        ) as response:
            try:
                response.raise_for_status()
            except aiohttp.ClientResponseError:
                LOGGER.info('Failing URL: %r', response.request_info.url)
                raise
            response_json = await response.json()
            return get_response_dict_by_doi_map(response_json)

    async def iter_article_mention_with_article_meta(
        self,
        article_mention_iterable: AsyncIterable[ArticleMention]
    ) -> AsyncIterator[ArticleMention]:
        article_mention_list = await get_list_for_async_iterable(article_mention_iterable)
        article_dois = {
            item.article_doi
            for item in article_mention_list
        }
        if not article_dois:
            for article_mention in article_mention_list:
                yield article_mention
            return
        article_meta_by_doi_map = get_article_meta_by_doi_map_for_response_dict_mapping(
            await self.get_batch_crossref_metadata_dict_by_doi(list(article_dois))
        )
        for article_mention in iter_article_mention_with_replaced_article_meta(
            article_mention_list,
            article_meta_by_doi_map=article_meta_by_doi_map
        ):
            yield article_mention
