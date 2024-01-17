from unittest.mock import MagicMock

import pytest


@pytest.fixture(name='app_providers_and_models_mock')
def _app_providers_and_models_mock() -> MagicMock:
    return MagicMock(name='app_providers_and_models')
