import logging
from datetime import datetime
from threading import Lock
from typing import Callable, Optional, TypeVar
from sciety_discovery.utils.bigquery import get_bq_table_modified_datetime

from sciety_discovery.utils.cache import (
    SingleObjectCache
)


LOGGER = logging.getLogger(__name__)


T = TypeVar('T')


class BigQueryTableModifiedInMemorySingleObjectCache(SingleObjectCache[T]):
    def __init__(
        self,
        gcp_project_name: str,
        table_id: str
    ) -> None:
        self.gcp_project_name = gcp_project_name
        self.table_id = table_id
        self._lock = Lock()
        self._value: Optional[T] = None
        self._last_table_modified_datetime: Optional[datetime] = None

    def get_table_last_modified_datetime(self):
        return get_bq_table_modified_datetime(
            project_name=self.gcp_project_name,
            table_id=self.table_id
        )

    def get_or_load(self, load_fn: Callable[[], T]) -> T:
        with self._lock:
            last_modified_datetime = self.get_table_last_modified_datetime()
            if (
                self._last_table_modified_datetime
                and last_modified_datetime >= self._last_table_modified_datetime
            ):
                LOGGER.info(
                    'not updating data, upstream table not modified: %r',
                    last_modified_datetime
                )
                assert self._value is not None
                return self._value
            result = load_fn()
            assert result is not None
            self._value = result
            self._last_table_modified_datetime = last_modified_datetime
            return result
