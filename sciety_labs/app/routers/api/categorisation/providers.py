import logging
from typing import Mapping, Optional

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.routers.api.categorisation.typing import CategorisationResponseDict


LOGGER = logging.getLogger(__name__)


def get_categorisation_response_dict_for_opensearch_document_dict(
    document_dict: dict
) -> CategorisationResponseDict:
    crossref_opensearch_dict = document_dict.get('crossref')
    group_title = (
        crossref_opensearch_dict
        and crossref_opensearch_dict.get('group_title')
    )
    if not group_title:
        return {}
    return {
        'categories': [{
            'display_name': group_title
        }]
    }


class AsyncOpenSearchCategoriesProvider:
    def __init__(self, app_providers_and_models: AppProvidersAndModels):
        self.async_opensearch_client = app_providers_and_models.async_opensearch_client
        self.index_name = app_providers_and_models.opensearch_config.index_name

    async def get_categories_dict_by_doi(
        self,
        article_doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> CategorisationResponseDict:
        return get_categorisation_response_dict_for_opensearch_document_dict(
            await self.async_opensearch_client.get_source(
                index=self.index_name,
                id=article_doi,
                _source_includes=['crossref.group_title'],
                headers=headers
            )
        )
