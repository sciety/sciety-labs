import logging
from datetime import timedelta
from pathlib import Path
from typing import Optional
import aiohttp

import aiohttp_client_cache
import requests_cache

import opensearchpy

from sciety_labs.aggregators.article import ArticleAggregator

from sciety_labs.models.evaluation import ScietyEventEvaluationStatsModel

from sciety_labs.models.lists import ScietyEventListsModel
from sciety_labs.providers.interfaces.article_recommendation import (
    ArticleRecommendationProvider,
    SingleArticleRecommendationProvider
)
from sciety_labs.providers.interfaces.async_article_recommendation import (
    AsyncSingleArticleRecommendationProvider
)
from sciety_labs.providers.crossref.async_providers import (
    AsyncCrossrefMetaDataProvider
)
from sciety_labs.providers.opensearch.async_providers import (
    AsyncOpenSearchArticleRecommendation
)
from sciety_labs.providers.semantic_scholar.async_providers import (
    AsyncSemanticScholarSearchProvider,
    AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider,
    get_async_semantic_scholar_provider
)
from sciety_labs.providers.crossref.providers import (
    CrossrefMetaDataProvider
)
from sciety_labs.providers.europepmc.async_providers import AsyncEuropePmcProvider
from sciety_labs.providers.google_sheet_image import (
    GoogleSheetArticleImageProvider,
    GoogleSheetListImageProvider
)
from sciety_labs.providers.opensearch.client import (
    get_async_opensearch_client_or_none,
    get_opensearch_client_or_none
)
from sciety_labs.providers.opensearch.config import OpenSearchConnectionConfig
from sciety_labs.providers.opensearch.sync_providers import (
    OpenSearchArticleRecommendation
)
from sciety_labs.providers.papers.async_papers import AsyncPapersProvider
from sciety_labs.providers.sciety_event import ScietyEventProvider
from sciety_labs.providers.semantic_scholar.providers import (
    SemanticScholarProvider,
    SemanticScholarTitleAbstractEmbeddingVectorProvider,
    get_semantic_scholar_provider
)
from sciety_labs.utils.arrow_cache import ArrowTableDiskSingleObjectCache
from sciety_labs.utils.cache import (
    ChainedObjectCache,
    DiskSingleObjectCache,
    InMemorySingleObjectCache
)


LOGGER = logging.getLogger(__name__)


def get_article_recommendation_provider(
    semantic_scholar_provider: SemanticScholarProvider
) -> ArticleRecommendationProvider:
    return semantic_scholar_provider


def get_opensearch_single_article_recommendation_provider(
    opensearch_client: opensearchpy.OpenSearch,
    opensearch_config: OpenSearchConnectionConfig,
    crossref_metadata_provider: CrossrefMetaDataProvider,
    title_abstract_embedding_vector_provider: SemanticScholarTitleAbstractEmbeddingVectorProvider
) -> Optional[SingleArticleRecommendationProvider]:
    assert opensearch_config.embedding_vector_mapping_name
    return OpenSearchArticleRecommendation(
        opensearch_client=opensearch_client,
        index_name=opensearch_config.index_name,
        embedding_vector_mapping_name=opensearch_config.embedding_vector_mapping_name,
        crossref_metadata_provider=crossref_metadata_provider,
        title_abstract_embedding_vector_provider=title_abstract_embedding_vector_provider
    )


def get_single_article_recommendation_provider(
    opensearch_client: Optional[opensearchpy.OpenSearch],
    opensearch_config: Optional[OpenSearchConnectionConfig],
    crossref_metadata_provider: CrossrefMetaDataProvider,
    title_abstract_embedding_vector_provider: SemanticScholarTitleAbstractEmbeddingVectorProvider
) -> Optional[SingleArticleRecommendationProvider]:
    if opensearch_client and opensearch_config and opensearch_config.embedding_vector_mapping_name:
        return get_opensearch_single_article_recommendation_provider(
            opensearch_client=opensearch_client,
            opensearch_config=opensearch_config,
            crossref_metadata_provider=crossref_metadata_provider,
            title_abstract_embedding_vector_provider=title_abstract_embedding_vector_provider
        )
    return None


def get_async_opensearch_single_article_recommendation_provider(
    opensearch_client: opensearchpy.AsyncOpenSearch,
    opensearch_config: OpenSearchConnectionConfig,
    crossref_metadata_provider: AsyncCrossrefMetaDataProvider,
    title_abstract_embedding_vector_provider: (
        AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider
    )
) -> Optional[AsyncSingleArticleRecommendationProvider]:
    assert opensearch_config.embedding_vector_mapping_name
    return AsyncOpenSearchArticleRecommendation(
        opensearch_client=opensearch_client,
        index_name=opensearch_config.index_name,
        embedding_vector_mapping_name=opensearch_config.embedding_vector_mapping_name,
        crossref_metadata_provider=crossref_metadata_provider,
        title_abstract_embedding_vector_provider=title_abstract_embedding_vector_provider
    )


def get_async_single_article_recommendation_provider(
    opensearch_client: Optional[opensearchpy.AsyncOpenSearch],
    opensearch_config: Optional[OpenSearchConnectionConfig],
    crossref_metadata_provider: AsyncCrossrefMetaDataProvider,
    title_abstract_embedding_vector_provider: (
        AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider
    )
) -> Optional[AsyncSingleArticleRecommendationProvider]:
    if opensearch_client and opensearch_config and opensearch_config.embedding_vector_mapping_name:
        return get_async_opensearch_single_article_recommendation_provider(
            opensearch_client=opensearch_client,
            opensearch_config=opensearch_config,
            crossref_metadata_provider=crossref_metadata_provider,
            title_abstract_embedding_vector_provider=title_abstract_embedding_vector_provider
        )
    return None


class AppProvidersAndModels:  # pylint: disable=too-many-instance-attributes
    def __init__(self):
        gcp_project_name = 'elife-data-pipeline'
        # Note: we allow for a longer max age.
        #   The update manager will request an update at an hourly rate.
        max_age_in_seconds = 24 * 60 * 60  # 1 day

        cache_dir = Path('.cache')
        cache_dir.mkdir(parents=True, exist_ok=True)

        sciety_event_query_results_cache = ChainedObjectCache([
            InMemorySingleObjectCache(
                max_age_in_seconds=max_age_in_seconds
            ),
            ArrowTableDiskSingleObjectCache(
                file_path=cache_dir / 'sciety_event_query_results_cache.parquet',
                max_age_in_seconds=max_age_in_seconds
            )
        ])

        cached_requests_session = requests_cache.CachedSession(
            '.cache/requests_cache',
            expire_after=timedelta(days=1),
            allowable_methods=('GET', 'HEAD', 'POST'),  # include POST for Semantic Scholar
            match_headers=False
        )
        self.cached_requests_session = cached_requests_session

        async_connector = aiohttp.TCPConnector(limit=1000)

        self.async_cached_client_session = aiohttp_client_cache.CachedSession(
            connector=async_connector,
            cache=aiohttp_client_cache.SQLiteBackend(
                '.cache/aiohttp-requests.sqlite',
                expire_after=timedelta(days=1),
                allowed_methods=('GET', 'HEAD', 'POST'),  # include POST for Semantic Scholar
                include_headers=False
            )
        )
        async_cached_client_session = self.async_cached_client_session

        async_client_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=200)
        )

        self.opensearch_config = OpenSearchConnectionConfig.from_env()
        self.opensearch_client = get_opensearch_client_or_none(
            self.opensearch_config,
            requests_session=cached_requests_session
        )
        LOGGER.info('opensearch_client: %r', self.opensearch_client)
        self.async_opensearch_client = get_async_opensearch_client_or_none(
            self.opensearch_config,
            client_session=async_client_session
        )
        LOGGER.info('async_opensearch_client: %r', self.async_opensearch_client)

        self.sciety_event_provider = ScietyEventProvider(
            gcp_project_name=gcp_project_name,
            query_results_cache=sciety_event_query_results_cache
        )

        self.lists_model = ScietyEventListsModel([])
        self.evaluation_stats_model = ScietyEventEvaluationStatsModel([])

        self.async_paper_provider = AsyncPapersProvider(
            client_session=async_cached_client_session
        )

        self.crossref_metadata_provider = CrossrefMetaDataProvider(
            requests_session=cached_requests_session
        )
        self.async_crossref_metadata_provider = AsyncCrossrefMetaDataProvider(
            client_session=async_cached_client_session
        )

        self.semantic_scholar_provider = get_semantic_scholar_provider(
            requests_session=cached_requests_session
        )
        self.async_semantic_scholar_provider = get_async_semantic_scholar_provider(
            client_session=async_cached_client_session
        )
        self.semantic_scholar_search_provider = AsyncSemanticScholarSearchProvider(
            async_semantic_scholar_provider=self.async_semantic_scholar_provider,
            evaluation_stats_model=self.evaluation_stats_model
        )
        title_abstract_embedding_vector_provider = (
            SemanticScholarTitleAbstractEmbeddingVectorProvider(
                requests_session=cached_requests_session
            )
        )
        self.async_title_abstract_embedding_vector_provider = (
            AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider(
                client_session=async_cached_client_session
            )
        )
        self.article_recommendation_provider = get_article_recommendation_provider(
            semantic_scholar_provider=self.semantic_scholar_provider
        )
        self.single_article_recommendation_provider = get_single_article_recommendation_provider(
            opensearch_client=self.opensearch_client,
            opensearch_config=self.opensearch_config,
            crossref_metadata_provider=self.crossref_metadata_provider,
            title_abstract_embedding_vector_provider=title_abstract_embedding_vector_provider
        )
        LOGGER.info(
            'single_article_recommendation_provider: %r',
            self.single_article_recommendation_provider
        )
        self.async_single_article_recommendation_provider = (
            get_async_single_article_recommendation_provider(
                opensearch_client=self.async_opensearch_client,
                opensearch_config=self.opensearch_config,
                crossref_metadata_provider=self.async_crossref_metadata_provider,
                title_abstract_embedding_vector_provider=(
                    self.async_title_abstract_embedding_vector_provider
                )
            )
        )
        LOGGER.info(
            'async_single_article_recommendation_provider: %r',
            self.async_single_article_recommendation_provider
        )

        self.europe_pmc_provider = AsyncEuropePmcProvider(
            client_session=async_cached_client_session
        )

        article_image_mapping_cache = ChainedObjectCache([
            InMemorySingleObjectCache(
                max_age_in_seconds=max_age_in_seconds
            ),
            DiskSingleObjectCache(
                file_path=cache_dir / 'article_image_mapping_cache.pickle',
                max_age_in_seconds=max_age_in_seconds
            )
        ])

        self.google_sheet_article_image_provider = GoogleSheetArticleImageProvider(
            image_mapping_cache=article_image_mapping_cache,
            refresh_manually=True
        )

        list_image_mapping_cache = ChainedObjectCache([
            InMemorySingleObjectCache(
                max_age_in_seconds=max_age_in_seconds
            ),
            DiskSingleObjectCache(
                file_path=cache_dir / 'list_image_mapping_cache.pickle',
                max_age_in_seconds=max_age_in_seconds
            )
        ])

        self.google_sheet_list_image_provider = GoogleSheetListImageProvider(
            image_mapping_cache=list_image_mapping_cache,
            refresh_manually=True
        )

        self.article_aggregator = ArticleAggregator(
            evaluation_stats_model=self.evaluation_stats_model,
            crossref_metadata_provider=self.crossref_metadata_provider,
            async_crossref_metadata_provider=self.async_crossref_metadata_provider,
            google_sheet_article_image_provider=self.google_sheet_article_image_provider
        )
