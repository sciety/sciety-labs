from typing import Iterable
from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient

from sciety_labs.app import main as main_module
from sciety_labs.app.main import create_app


@pytest.fixture(name='app_providers_and_models_class_mock', autouse=True)
def _app_providers_and_models_class_mock(
    app_providers_and_models_mock: MagicMock
) -> Iterable[MagicMock]:
    with patch.object(main_module, 'AppProvidersAndModels') as mock:
        mock.return_value = app_providers_and_models_mock
        yield mock


def test_read_main():
    client = TestClient(create_app())
    response = client.get('/')
    assert response.status_code == 200
