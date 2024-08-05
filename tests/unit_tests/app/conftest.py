from unittest.mock import AsyncMock, MagicMock

import aiohttp_client_cache
import aiohttp_client_cache.backends
import aiohttp_client_cache.backends.base
import aiohttp_client_cache.session
import opensearchpy
import pytest

from sciety_labs.providers.interfaces.async_article_recommendation import (
    AsyncSingleArticleRecommendationProvider
)


@pytest.fixture(name='app_providers_and_models_mock')
def _app_providers_and_models_mock() -> MagicMock:
    return MagicMock(name='app_providers_and_models_mock')


@pytest.fixture(name='async_cached_client_session_mock', autouse=True)
def _async_cached_client_session_mock(
    app_providers_and_models_mock: MagicMock
) -> AsyncMock:
    mock = AsyncMock(aiohttp_client_cache.session.CachedSession)
    mock.cache = AsyncMock(aiohttp_client_cache.backends.base.CacheBackend)
    app_providers_and_models_mock.async_cached_client_session = mock
    return mock


@pytest.fixture(name='async_single_article_recommendation_provider_mock', autouse=True)
def _async_single_article_recommendation_provider_mock(
    app_providers_and_models_mock: MagicMock
) -> AsyncMock:
    mock = AsyncMock(AsyncSingleArticleRecommendationProvider)
    app_providers_and_models_mock.async_single_article_recommendation_provider = mock
    return mock


@pytest.fixture(name='async_opensearch_client_mock', autouse=True)
def _async_opensearch_client_mock(
    app_providers_and_models_mock: MagicMock
) -> AsyncMock:
    mock = AsyncMock(opensearchpy.AsyncOpenSearch)
    mock.get_source = AsyncMock(name='AsyncOpenSearch.get_source')
    mock.search = AsyncMock(name='AsyncOpenSearch.search')
    app_providers_and_models_mock.async_opensearch_client = mock
    return mock


@pytest.fixture(autouse=True)
def get_article_recommendation_list_for_article_doi_mock(
    async_single_article_recommendation_provider_mock: AsyncMock
) -> AsyncMock:
    return (
        async_single_article_recommendation_provider_mock
        .get_article_recommendation_list_for_article_doi
    )
