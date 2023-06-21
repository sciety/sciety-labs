import logging
from pathlib import Path
from time import monotonic
from typing import Optional, Sequence

import objsize
import pyarrow

from sciety_labs.utils.bigquery import get_arrow_table_from_bq_query
from sciety_labs.providers.sql import get_sql_path
from sciety_labs.utils.cache import DummySingleObjectCache, SingleObjectCache


LOGGER = logging.getLogger(__name__)


class ScietyEventProvider:
    def __init__(
        self,
        gcp_project_name: str = 'elife-data-pipeline',
        query_results_cache: Optional[SingleObjectCache[pyarrow.Table]] = None
    ):
        self.gcp_project_name = gcp_project_name
        self.get_sciety_events_query = (
            Path(get_sql_path('get_sciety_events.sql')).read_text(encoding='utf-8')
        )
        if query_results_cache is None:
            query_results_cache = DummySingleObjectCache[pyarrow.Table]()
        self._query_results_cache = query_results_cache

    def _load_query_results_from_bq_as_arrow_table(self) -> pyarrow.Table:
        LOGGER.info('Loading query results from BigQuery...')
        start_time = monotonic()
        arrow_table = get_arrow_table_from_bq_query(
            self.gcp_project_name,
            self.get_sciety_events_query
        )
        end_time = monotonic()
        LOGGER.info(
            'Loaded query results from BigQuery, rows=%d, approx_size=%.3fMB, time=%.3f seconds',
            len(arrow_table),
            objsize.get_deep_size(arrow_table) / 1024 / 1024,
            (end_time - start_time)
        )
        return arrow_table

    def get_sciety_event_dict_list(self) -> Sequence[dict]:
        arrow_table = self._query_results_cache.get_or_load(
            load_fn=self._load_query_results_from_bq_as_arrow_table
        )
        start_time = monotonic()
        # Note: to_pylist is quite slow, e.g. 20 seconds vs 1.6 seconds
        query_results = arrow_table.to_pandas().to_dict(orient='records')
        end_time = monotonic()
        LOGGER.info(
            'Query results as list, rows=%d, approx_size=%.3fMB, time=%.3f seconds',
            len(query_results),
            objsize.get_deep_size(query_results) / 1024 / 1024,
            (end_time - start_time)
        )
        return query_results
