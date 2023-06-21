from datetime import timedelta
from pathlib import Path

import requests_cache
from sciety_labs.aggregators.article import ArticleAggregator

from sciety_labs.models.evaluation import ScietyEventEvaluationStatsModel

from sciety_labs.models.lists import ScietyEventListsModel
from sciety_labs.providers.crossref import (
    CrossrefMetaDataProvider
)
from sciety_labs.providers.europe_pmc import EuropePmcProvider
from sciety_labs.providers.google_sheet_image import (
    GoogleSheetArticleImageProvider,
    GoogleSheetListImageProvider
)
from sciety_labs.providers.sciety_event import ScietyEventProvider
from sciety_labs.providers.semantic_scholar import (
    SemanticScholarSearchProvider,
    get_semantic_scholar_provider
)
from sciety_labs.providers.semantic_scholar_bigquery_mapping import (
    SemanticScholarBigQueryMappingProvider
)
from sciety_labs.providers.twitter import get_twitter_user_article_list_provider_or_none
from sciety_labs.utils.arrow_cache import ArrowTableDiskSingleObjectCache
from sciety_labs.utils.bq_cache import BigQueryTableModifiedInMemorySingleObjectCache
from sciety_labs.utils.cache import (
    ChainedObjectCache,
    DiskSingleObjectCache,
    InMemorySingleObjectCache
)


class AppProvidersAndModels:  # pylint: disable=too-many-instance-attributes
    def __init__(self):
        gcp_project_name = 'elife-data-pipeline'
        sciety_event_table_id = f'{gcp_project_name}.de_proto.sciety_event_v1'
        semantic_scholar_response_table_id = (
            f'{gcp_project_name}.prod.semantic_scholar_responses_v1'
        )
        max_age_in_seconds = 60 * 60  # 1 hour

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

        cached_requests_session = requests_cache.CachedSession(
            '.cache/requests_cache',
            xpire_after=timedelta(days=1),
            allowable_methods=('GET', 'HEAD', 'POST'),  # include POST for Semantic Scholar
            match_headers=False
        )

        self.sciety_event_provider = ScietyEventProvider(
            gcp_project_name=gcp_project_name,
            query_results_cache=sciety_event_query_results_cache
        )

        self.semantic_scholar_mapping_provider = SemanticScholarBigQueryMappingProvider(
            gcp_project_name=gcp_project_name,
            query_results_cache=semantic_scholar_mapping_query_results_cache
        )

        self.lists_model = ScietyEventListsModel([])
        self.evaluation_stats_model = ScietyEventEvaluationStatsModel([])

        self.twitter_user_article_list_provider = get_twitter_user_article_list_provider_or_none(
            requests_session=cached_requests_session
        )

        self.crossref_metadata_provider = CrossrefMetaDataProvider(
            requests_session=cached_requests_session
        )

        self.semantic_scholar_provider = get_semantic_scholar_provider(
            requests_session=cached_requests_session
        )
        self.semantic_scholar_search_provider = SemanticScholarSearchProvider(
            semantic_scholar_provider=self.semantic_scholar_provider,
            evaluation_stats_model=self.evaluation_stats_model
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
