from unittest.mock import patch, MagicMock
from typing import Iterable

import pytest

from google.cloud.bigquery.table import Row

from sciety_labs.utils import bigquery as bigquery_module
from sciety_labs.utils.bigquery import iter_dict_from_bq_query


@pytest.fixture(name='bigquery_mock')
def _bigquery_mock() -> Iterable[MagicMock]:
    with patch.object(bigquery_module, 'bigquery') as mock:
        yield mock


@pytest.fixture(name='bq_client_mock')
def _bq_client_mock(bigquery_mock: MagicMock) -> MagicMock:
    return bigquery_mock.Client


class TestIterDictFromBqQuery:
    def test_should_return_dict_for_row(self, bq_client_mock: MagicMock):
        mock_query_job = bq_client_mock.return_value.query.return_value
        mock_query_job.result.return_value = [
            Row(['value1', 'value2'], {'key1': 0, 'key2': 1})
        ]
        result = list(iter_dict_from_bq_query(
            project_name='project1',
            query='query1'
        ))
        assert result == [{
            'key1': 'value1',
            'key2': 'value2'
        }]
