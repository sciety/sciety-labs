import functools
import logging
import os
import pickle
import time
from pathlib import Path
from time import monotonic
from threading import Lock
from typing import IO, Callable, Optional,  Protocol, Sequence, TypeVar


LOGGER = logging.getLogger(__name__)


T = TypeVar('T')


class SingleObjectCache(Protocol[T]):
    def get_or_load(self, load_fn: Callable[[], T]) -> T:
        pass


class ChainedObjectCache(SingleObjectCache[T]):
    def __init__(self, cache_list: Sequence[SingleObjectCache[T]]):
        assert len(cache_list) >= 1
        self.cache_list = cache_list

    def get_or_load(self, load_fn: Callable[[], T]) -> T:
        wrapped_load_fn = load_fn
        previous_cache_list = self.cache_list[:-1]
        last_cache = self.cache_list[-1]
        for previous_cache in previous_cache_list:
            wrapped_load_fn = functools.partial(
                previous_cache.get_or_load,
                load_fn=wrapped_load_fn
            )
        return last_cache.get_or_load(load_fn=wrapped_load_fn)


class DummySingleObjectCache(SingleObjectCache[T]):
    def get_or_load(self, load_fn: Callable[[], T]) -> T:
        return load_fn()


class InMemorySingleObjectCache(SingleObjectCache[T]):
    def __init__(
        self,
        max_age_in_seconds: float
    ) -> None:
        self.max_age_in_seconds = max_age_in_seconds
        self._lock = Lock()
        self._value: Optional[T] = None
        self._last_updated_time: Optional[float] = None

    def _is_max_age_reached(self, now: float) -> bool:
        return bool(
            self._last_updated_time is not None
            and (now - self._last_updated_time > self.max_age_in_seconds)
        )

    def get_or_load(self, load_fn: Callable[[], T]) -> T:
        with self._lock:
            now = monotonic()
            result = self._value
            if result is not None and not self._is_max_age_reached(now):
                return result
            result = load_fn()
            assert result is not None
            self._value = result
            self._last_updated_time = now
            return result


class DiskSingleObjectCache(SingleObjectCache[T]):
    def __init__(
        self,
        file_path: Path,
        max_age_in_seconds: float,
        serialize_fn: Callable[[T, IO], None] = pickle.dump,
        deserialize_fn: Callable[[IO], T] = pickle.load
    ) -> None:
        self.file_path = file_path
        self.max_age_in_seconds = max_age_in_seconds
        self.serialize_fn = serialize_fn
        self.deserialize_fn = deserialize_fn
        self._lock = Lock()
        self._value: Optional[T] = None
        self._last_updated_time: Optional[float] = None

    def _is_max_age_reached(self) -> bool:
        modified_time = os.path.getmtime(self.file_path)
        age = time.time() - modified_time
        LOGGER.debug('age: %r', age)
        return age >= self.max_age_in_seconds

    def get_or_load(self, load_fn: Callable[[], T]) -> T:
        with self._lock:
            if self.file_path.exists() and not self._is_max_age_reached():
                with self.file_path.open('rb') as file_fp:
                    return self.deserialize_fn(file_fp)
            result = load_fn()
            assert result is not None
            with self.file_path.open('wb') as file_fp:
                self.serialize_fn(result, file_fp)
            return result
