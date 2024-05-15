import logging
from typing import Mapping, Optional

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels


LOGGER = logging.getLogger(__name__)


class AsyncOpenSearchCategoriesProvider:
    def __init__(self, app_providers_and_models: AppProvidersAndModels):
        self.async_opensearch_client = app_providers_and_models.async_opensearch_client
        self.index_name = app_providers_and_models.opensearch_config.index_name

    async def get_categories_dict_by_doi(
        self,
        article_doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> dict:
        doc = await (
            self.async_opensearch_client.get_source(
                index=self.index_name,
                id=article_doi,
                _source_includes=['crossref.group_title'],
                headers=headers
            )
        )
        return doc
