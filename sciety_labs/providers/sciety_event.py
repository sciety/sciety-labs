import logging
from time import monotonic
from typing import Sequence

import objsize

from sciety_labs.providers.bigquery_provider import BigQueryArrowTableProvider


LOGGER = logging.getLogger(__name__)


class ScietyEventProvider(BigQueryArrowTableProvider):
    def __init__(self, **kwargs):
        super().__init__(
            name='Sciety Event',
            query_file_name='get_sciety_events.sql',
            **kwargs
        )

    def get_sciety_event_dict_list(self) -> Sequence[dict]:
        arrow_table = self.get_arrow_table()
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
