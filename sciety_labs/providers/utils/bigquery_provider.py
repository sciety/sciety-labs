import logging
from pathlib import Path
from time import monotonic
from typing import Optional

import objsize
import pyarrow

from sciety_labs.utils.bigquery import get_arrow_table_from_bq_query
from sciety_labs.providers.sql import get_sql_path
from sciety_labs.utils.cache import DummySingleObjectCache, SingleObjectCache


LOGGER = logging.getLogger(__name__)


class BigQueryArrowTableProvider:
    def __init__(
        self,
        name: str,
        query_file_name: str,
        gcp_project_name: str = 'elife-data-pipeline',
        query_results_cache: Optional[SingleObjectCache[pyarrow.Table]] = None
    ):
        self.name = name
        self.gcp_project_name = gcp_project_name
        self.query = (
            Path(get_sql_path(query_file_name)).read_text(encoding='utf-8')
        )
        if query_results_cache is None:
            query_results_cache = DummySingleObjectCache[pyarrow.Table]()
        self._query_results_cache = query_results_cache

    def _load_query_results_from_bq_as_arrow_table(self) -> pyarrow.Table:
        LOGGER.info('Loading %s query results from BigQuery...', self.name)
        start_time = monotonic()
        arrow_table = get_arrow_table_from_bq_query(
            self.gcp_project_name,
            self.query
        )
        end_time = monotonic()
        LOGGER.info(
            (
                'Loaded %s query results from BigQuery'
                ', rows=%d, approx_size=%.3fMB, time=%.3f seconds'
            ),
            self.name,
            len(arrow_table),
            objsize.get_deep_size(arrow_table) / 1024 / 1024,
            (end_time - start_time)
        )
        return arrow_table

    def get_arrow_table(self) -> pyarrow.Table:
        return self._query_results_cache.get_or_load(
            load_fn=self._load_query_results_from_bq_as_arrow_table
        )

    def preload(self):
        self.get_arrow_table()

    def refresh(self):
        self._query_results_cache.reload(
            load_fn=self._load_query_results_from_bq_as_arrow_table
        )
