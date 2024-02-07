from typing import Iterator
from urllib.parse import urljoin

import pytest

from requests import Session


class RegressionTestSession(Session):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url

    def request(self, method, url, *args, **kwargs):
        joined_url = urljoin(self.base_url, url)
        return super().request(method, joined_url, *args, **kwargs)


def get_regression_test_base_url() -> str:
    return 'http://localhost:8000'


@pytest.fixture()
def regression_test_session() -> Iterator[Session]:
    with RegressionTestSession(get_regression_test_base_url()) as session:
        yield session
