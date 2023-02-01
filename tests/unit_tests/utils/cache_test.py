from unittest.mock import MagicMock, patch
from typing import Iterable

import pytest

import sciety_discovery.utils.cache as cache_module
from sciety_discovery.utils.cache import (
    InMemorySingleObjectCache
)


@pytest.fixture(name='monotonic_mock')
def _monotonic_mock() -> Iterable[MagicMock]:
    with patch.object(cache_module, 'monotonic') as mock:
        yield mock


class TestInMemorySingleObjectCache:
    def test_should_get_loaded_value(self):
        cache = InMemorySingleObjectCache(max_age_in_seconds=10)
        result = cache.get_or_load(load_fn=lambda: 'value_1')
        assert result == 'value_1'

    def test_should_not_call_load_function_multiple_times(self):
        cache = InMemorySingleObjectCache(max_age_in_seconds=10)
        load_fn = MagicMock(name='load_fn')
        load_fn.return_value = 'value_1'
        cache.get_or_load(load_fn=load_fn)
        result = cache.get_or_load(load_fn=load_fn)
        assert result == 'value_1'
        assert load_fn.call_count == 1

    def test_should_reload_if_max_age_reached(self, monotonic_mock: MagicMock):
        cache = InMemorySingleObjectCache[str](
            max_age_in_seconds=60
        )
        load_fn = MagicMock(name='load_fn')
        load_fn.side_effect = ['value_1', 'value_2']
        monotonic_mock.return_value = 100
        cache.get_or_load(load_fn=load_fn)
        monotonic_mock.return_value = 200
        result = cache.get_or_load(load_fn=load_fn)
        assert result == 'value_2'
        assert load_fn.call_count == 2
