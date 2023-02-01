import logging
from pathlib import Path
from time import monotonic
from typing import Sequence

from sciety_discovery.utils.bigquery import iter_dict_from_bq_query
from sciety_discovery.providers.sql import get_sql_path


LOGGER = logging.getLogger(__name__)


class ScietyEventProvider:
    def __init__(self, gcp_project_name: str = 'elife-data-pipeline'):
        self.gcp_project_name = gcp_project_name
        self.get_sciety_events_query = (
            Path(get_sql_path('get_sciety_events.sql')).read_text(encoding='utf-8')
        )

    def get_sciety_event_dict_list(self) -> Sequence[dict]:
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
