import logging
from typing import Iterable
from unittest.mock import patch

import pytest


@pytest.fixture(scope='session', autouse=True)
def setup_logging():
    logging.basicConfig(level='INFO')
    for name in ['tests', 'sciety_discovery']:
        logging.getLogger(name).setLevel('DEBUG')


@pytest.fixture()
def env_mock() -> Iterable[dict]:
    env_dict: dict = {}
    with patch('os.environ', env_dict):
        yield env_dict
