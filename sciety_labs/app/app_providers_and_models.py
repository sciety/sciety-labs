from datetime import timedelta
from pathlib import Path

import requests_cache

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
from sciety_labs.providers.twitter import get_twitter_user_article_list_provider_or_none
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
        max_age_in_seconds = 60 * 60  # 1 hour

        cache_dir = Path('.cache')
        cache_dir.mkdir(parents=True, exist_ok=True)

        query_results_cache = ChainedObjectCache([
            BigQueryTableModifiedInMemorySingleObjectCache(
                gcp_project_name=gcp_project_name,
                table_id=sciety_event_table_id
            ),
            DiskSingleObjectCache(
                file_path=cache_dir / 'query_results_cache.pickle',
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
            query_results_cache=query_results_cache
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
