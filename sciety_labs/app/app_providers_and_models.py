import logging
from datetime import timedelta
from pathlib import Path
from typing import Optional

import requests_cache

from opensearchpy import OpenSearch

from sciety_labs.aggregators.article import ArticleAggregator

from sciety_labs.models.evaluation import ScietyEventEvaluationStatsModel

from sciety_labs.models.lists import ScietyEventListsModel
from sciety_labs.providers.article_recommendation import (
    ArticleRecommendationProvider,
    SingleArticleRecommendationProvider
)
from sciety_labs.providers.async_semantic_scholar import (
    AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider
)
from sciety_labs.providers.crossref import (
    CrossrefMetaDataProvider
)
from sciety_labs.providers.europe_pmc import EuropePmcProvider
from sciety_labs.providers.google_sheet_image import (
    GoogleSheetArticleImageProvider,
    GoogleSheetListImageProvider
)
from sciety_labs.providers.opensearch import (
    OpenSearchConnectionConfig,
    get_async_opensearch_client_or_none,
    get_opensearch_client_or_none
)
from sciety_labs.providers.opensearch_article_recommendation import OpenSearchArticleRecommendation
from sciety_labs.providers.sciety_event import ScietyEventProvider
from sciety_labs.providers.semantic_scholar import (
    SemanticScholarProvider,
    SemanticScholarSearchProvider,
    SemanticScholarTitleAbstractEmbeddingVectorProvider,
    get_semantic_scholar_provider
)
from sciety_labs.providers.semantic_scholar_bigquery_mapping import (
    SemanticScholarBigQueryMappingProvider
)
from sciety_labs.providers.semantic_scholar_mapping import SemanticScholarMappingProvider
from sciety_labs.providers.semantic_scholar_opensearch_mapping import (
    SemanticScholarOpenSearchMappingProvider
)
from sciety_labs.providers.twitter import get_twitter_user_article_list_provider_or_none
from sciety_labs.utils.arrow_cache import ArrowTableDiskSingleObjectCache
from sciety_labs.utils.bq_cache import BigQueryTableModifiedInMemorySingleObjectCache
from sciety_labs.utils.cache import (
    ChainedObjectCache,
    DiskSingleObjectCache,
    InMemorySingleObjectCache
)


LOGGER = logging.getLogger(__name__)


def get_semantic_scholar_bigquery_mapping_provider(
    gcp_project_name: str,
    cache_dir: Path,
    max_age_in_seconds: int
) -> SemanticScholarMappingProvider:
    semantic_scholar_response_table_id = (
        f'{gcp_project_name}.prod.semantic_scholar_responses_v1'
    )
    semantic_scholar_mapping_query_results_cache = ChainedObjectCache([
        BigQueryTableModifiedInMemorySingleObjectCache(
            gcp_project_name=gcp_project_name,
            table_id=semantic_scholar_response_table_id
        ),
        ArrowTableDiskSingleObjectCache(
            file_path=cache_dir / 'semantic_scholar_mapping_query_results_cache.parquet',
            max_age_in_seconds=max_age_in_seconds
        )
    ])

    return SemanticScholarBigQueryMappingProvider(
        gcp_project_name=gcp_project_name,
        query_results_cache=semantic_scholar_mapping_query_results_cache
    )


def get_semantic_scholar_opensearch_mapping_provider(
    opensearch_client: OpenSearch,
    opensearch_config: OpenSearchConnectionConfig
) -> SemanticScholarMappingProvider:
    LOGGER.info('Using OpenSearch index: %r', opensearch_config.index_name)
    return SemanticScholarOpenSearchMappingProvider(
        opensearch_client=opensearch_client,
        index_name=opensearch_config.index_name
    )


def get_semantic_scholar_mapping_provider(
    opensearch_client: Optional[OpenSearch],
    opensearch_config: Optional[OpenSearchConnectionConfig],
    gcp_project_name: str,
    cache_dir: Path,
    max_age_in_seconds: int
) -> SemanticScholarMappingProvider:
    if opensearch_client:
        assert opensearch_config is not None
        return get_semantic_scholar_opensearch_mapping_provider(
            opensearch_client=opensearch_client,
            opensearch_config=opensearch_config
        )
    return get_semantic_scholar_bigquery_mapping_provider(
        gcp_project_name=gcp_project_name,
        cache_dir=cache_dir,
        max_age_in_seconds=max_age_in_seconds
    )


def get_article_recommendation_provider(
    semantic_scholar_provider: SemanticScholarProvider
) -> ArticleRecommendationProvider:
    return semantic_scholar_provider


def get_opensearch_single_article_recommendation_provider(
    opensearch_client: OpenSearch,
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
    opensearch_client: Optional[OpenSearch],
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


class AppProvidersAndModels:  # pylint: disable=too-many-instance-attributes
    def __init__(self):
        gcp_project_name = 'elife-data-pipeline'
        sciety_event_table_id = f'{gcp_project_name}.de_proto.sciety_event_v1'
        # Note: we allow for a longer max age.
        #   The update manager will request an update at an hourly rate.
        max_age_in_seconds = 24 * 60 * 60  # 1 day

        cache_dir = Path('.cache')
        cache_dir.mkdir(parents=True, exist_ok=True)

        sciety_event_query_results_cache = ChainedObjectCache([
            BigQueryTableModifiedInMemorySingleObjectCache(
                gcp_project_name=gcp_project_name,
                table_id=sciety_event_table_id
            ),
            ArrowTableDiskSingleObjectCache(
                file_path=cache_dir / 'sciety_event_query_results_cache.parquet',
                max_age_in_seconds=max_age_in_seconds
            )
        ])

        cached_requests_session = requests_cache.CachedSession(
            '.cache/requests_cache',
            xpire_after=timedelta(days=1),
            allowable_methods=('GET', 'HEAD', 'POST'),  # include POST for Semantic Scholar
            match_headers=False
        )

        self.opensearch_config = OpenSearchConnectionConfig.from_env()
        opensearch_client = get_opensearch_client_or_none(
            self.opensearch_config,
            requests_session=cached_requests_session
        )
        LOGGER.info('opensearch_client: %r', opensearch_client)
        self.async_opensearch_client = get_async_opensearch_client_or_none(
            self.opensearch_config,
            requests_session=cached_requests_session
        )
        LOGGER.info('async_opensearch_client: %r', self.async_opensearch_client)

        self.sciety_event_provider = ScietyEventProvider(
            gcp_project_name=gcp_project_name,
            query_results_cache=sciety_event_query_results_cache
        )

        self.semantic_scholar_mapping_provider = get_semantic_scholar_mapping_provider(
            opensearch_client=opensearch_client,
            opensearch_config=self.opensearch_config,
            gcp_project_name=gcp_project_name,
            cache_dir=cache_dir,
            max_age_in_seconds=max_age_in_seconds
        )
        LOGGER.info('semantic_scholar_mapping_provider: %r', self.semantic_scholar_mapping_provider)

        self.lists_model = ScietyEventListsModel([])
        self.evaluation_stats_model = ScietyEventEvaluationStatsModel([])

        self.twitter_user_article_list_provider = get_twitter_user_article_list_provider_or_none(
            requests_session=cached_requests_session
        )

        self.crossref_metadata_provider = CrossrefMetaDataProvider(
            requests_session=cached_requests_session
        )

        self.semantic_scholar_provider = get_semantic_scholar_provider(
            requests_session=cached_requests_session,
            semantic_scholar_mapping_provider=self.semantic_scholar_mapping_provider
        )
        self.semantic_scholar_search_provider = SemanticScholarSearchProvider(
            semantic_scholar_provider=self.semantic_scholar_provider,
            evaluation_stats_model=self.evaluation_stats_model
        )
        title_abstract_embedding_vector_provider = (
            SemanticScholarTitleAbstractEmbeddingVectorProvider(
                requests_session=cached_requests_session
            )
        )
        self.async_title_abstract_embedding_vector_provider = (
            AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider(
                client_session=None
            )
        )
        self.article_recommendation_provider = get_article_recommendation_provider(
            semantic_scholar_provider=self.semantic_scholar_provider
        )
        self.single_article_recommendation_provider = get_single_article_recommendation_provider(
            opensearch_client=opensearch_client,
            opensearch_config=self.opensearch_config,
            crossref_metadata_provider=self.crossref_metadata_provider,
            title_abstract_embedding_vector_provider=title_abstract_embedding_vector_provider
        )
        LOGGER.info(
            'single_article_recommendation_provider: %r',
            self.single_article_recommendation_provider
        )

        self.europe_pmc_provider = EuropePmcProvider(
            requests_session=cached_requests_session
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
            google_sheet_article_image_provider=self.google_sheet_article_image_provider
        )
