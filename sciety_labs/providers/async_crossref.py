import logging
from typing import Mapping, Optional

from sciety_labs.models.article import ArticleMetaData
from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider
from sciety_labs.providers.crossref import (
    get_article_metadata_from_crossref_metadata
)


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
