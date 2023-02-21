import logging
from pathlib import Path
from time import monotonic
from typing import Optional, Sequence

from sciety_labs.utils.bigquery import iter_dict_from_bq_query
from sciety_labs.providers.sql import get_sql_path
from sciety_labs.utils.cache import DummySingleObjectCache, SingleObjectCache


LOGGER = logging.getLogger(__name__)


class ScietyEventProvider:
    def __init__(
        self,
        gcp_project_name: str = 'elife-data-pipeline',
        query_results_cache: Optional[SingleObjectCache[Sequence[dict]]] = None
    ):
        self.gcp_project_name = gcp_project_name
        self.get_sciety_events_query = (
            Path(get_sql_path('get_sciety_events.sql')).read_text(encoding='utf-8')
        )
        if query_results_cache is None:
            query_results_cache = DummySingleObjectCache[Sequence[dict]]()
        self._query_results_cache = query_results_cache

    def _load_query_results_from_bq(self) -> Sequence[dict]:
        LOGGER.info('Loading query results from BigQuery...')
        start_time = monotonic()
        result = list(iter_dict_from_bq_query(
            self.gcp_project_name,
            self.get_sciety_events_query
        ))
        end_time = monotonic()
        LOGGER.info(
            'Loaded query results from BigQuery, rows=%d, time=%.3f seconds',
            len(result),
            (end_time - start_time)
        )
        return result

    def get_sciety_event_dict_list(self) -> Sequence[dict]:
        return self._query_results_cache.get_or_load(
            load_fn=self._load_query_results_from_bq
        )
