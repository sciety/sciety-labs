from unittest.mock import AsyncMock, MagicMock

import pytest

from sciety_labs.providers.async_article_recommendation import (
    AsyncSingleArticleRecommendationProvider
)
from sciety_labs.providers.async_providers.crossref.providers import (
    AsyncCrossrefMetaDataProvider
)


@pytest.fixture(name='app_providers_and_models_mock')
def _app_providers_and_models_mock() -> MagicMock:
    return MagicMock(name='app_providers_and_models')


@pytest.fixture(name='async_crossref_metadata_provider_mock', autouse=True)
def _async_crossref_metadata_provider_mock(
    app_providers_and_models_mock: MagicMock
) -> AsyncMock:
    mock = AsyncMock(AsyncCrossrefMetaDataProvider)
    app_providers_and_models_mock.async_crossref_metadata_provider = mock
    return mock


@pytest.fixture(name='async_single_article_recommendation_provider_mock', autouse=True)
def _async_single_article_recommendation_provider_mock(
    app_providers_and_models_mock: MagicMock
) -> AsyncMock:
    mock = AsyncMock(AsyncSingleArticleRecommendationProvider)
    app_providers_and_models_mock.async_single_article_recommendation_provider = mock
    return mock


@pytest.fixture(autouse=True)
def get_article_recommendation_list_for_article_doi_mock(
    async_single_article_recommendation_provider_mock: AsyncMock
) -> AsyncMock:
    return (
        async_single_article_recommendation_provider_mock
        .get_article_recommendation_list_for_article_doi
    )
