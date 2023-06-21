from datetime import datetime
import logging
from typing import Any, Iterable, Optional, Sequence

import pyarrow

from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator

LOGGER = logging.getLogger(__name__)


def get_bq_client(project_name: str) -> bigquery.Client:
    return bigquery.Client(project=project_name)


def get_bq_result_from_bq_query(
    project_name: str,
    query: str,
    query_parameters: Optional[Sequence[Any]] = tuple()
) -> RowIterator:
    client = get_bq_client(project_name=project_name)
    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
    query_job = client.query(query, job_config=job_config)  # Make an API request.
    bq_result = query_job.result()  # Waits for query to finish
    LOGGER.debug('bq_result: %r', bq_result)
    return bq_result


def iter_dict_from_bq_query(
    project_name: str,
    query: str,
    query_parameters: Optional[Sequence[Any]] = tuple()
) -> Iterable[dict]:
    bq_result = get_bq_result_from_bq_query(
        project_name=project_name,
        query=query,
        query_parameters=query_parameters
    )
    for row in bq_result:
        LOGGER.debug('row: %r', row)
        yield dict(row.items())


def get_arrow_table_from_bq_query(
    project_name: str,
    query: str,
    query_parameters: Optional[Sequence[Any]] = tuple()
) -> pyarrow.Table:
    bq_result = get_bq_result_from_bq_query(
        project_name=project_name,
        query=query,
        query_parameters=query_parameters
    )
    return bq_result.to_arrow()


def get_bq_table_modified_datetime(
    project_name: str,
    table_id: str
) -> datetime:
    bq_client = get_bq_client(project_name=project_name)
    bq_table = bq_client.get_table(table_id)
    return bq_table.modified
