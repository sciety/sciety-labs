import functools
import logging
import os
import pickle
import time
from pathlib import Path
from time import monotonic
from threading import Lock
from typing import Callable, Optional,  Protocol, Sequence, TypeVar


LOGGER = logging.getLogger(__name__)


T = TypeVar('T')


class SingleObjectCache(Protocol[T]):
    def get_or_load(self, load_fn: Callable[[], T], reload: bool = False) -> T:
        pass

    def reload(self, load_fn: Callable[[], T]) -> T:
        pass

    def clear(self):
        pass


class BaseSingleObjectCache(SingleObjectCache[T]):
    def clear(self):
        pass

    def reload(self, load_fn: Callable[[], T]) -> T:
        return self.get_or_load(load_fn=load_fn, reload=True)


class ChainedObjectCache(BaseSingleObjectCache[T]):
    def __init__(self, cache_list: Sequence[SingleObjectCache[T]]):
        assert len(cache_list) >= 1
        self.cache_list = cache_list

    def get_or_load(self, load_fn: Callable[[], T], reload: bool = False) -> T:
        wrapped_load_fn = load_fn
        previous_cache_list = self.cache_list[:-1]
        last_cache = self.cache_list[-1]
        for previous_cache in previous_cache_list:
            wrapped_load_fn = functools.partial(
                previous_cache.get_or_load,
                load_fn=wrapped_load_fn,
                reload=reload
            )
        return last_cache.get_or_load(load_fn=wrapped_load_fn, reload=reload)

    def clear(self):
        for child_cache in self.cache_list:
            child_cache.clear()


class DummySingleObjectCache(BaseSingleObjectCache[T]):
    def get_or_load(self, load_fn: Callable[[], T], reload: bool = False) -> T:
        return load_fn()


class InMemorySingleObjectCache(BaseSingleObjectCache[T]):
    def __init__(
        self,
        max_age_in_seconds: Optional[float] = None
    ) -> None:
        self.max_age_in_seconds = max_age_in_seconds
        self._lock = Lock()
        self._value: Optional[T] = None
        self._last_updated_time: Optional[float] = None

    def _is_max_age_reached(self, now: float) -> bool:
        return bool(
            self._last_updated_time is not None
            and self.max_age_in_seconds
            and (now - self._last_updated_time > self.max_age_in_seconds)
        )

    def get_or_load(self, load_fn: Callable[[], T], reload: bool = False) -> T:
        with self._lock:
            now = monotonic()
            result = self._value
            if (
                not reload
                and result is not None
                and not self._is_max_age_reached(now)
            ):
                return result
            result = load_fn()
            assert result is not None
            self._value = result
            self._last_updated_time = now
            return result

    def clear(self):
        with self._lock:
            self._value = None
            self._last_updated_time = None


class DiskSingleObjectCache(BaseSingleObjectCache[T]):
    def __init__(
        self,
        file_path: Path,
        max_age_in_seconds: float
    ) -> None:
        self.file_path = file_path
        self.max_age_in_seconds = max_age_in_seconds
        self._lock = Lock()
        self._value: Optional[T] = None
        self._last_updated_time: Optional[float] = None

    def serialize_to_file(self, obj: T, file_path: str) -> T:
        with open(file_path, 'wb') as file_fp:
            pickle.dump(obj, file_fp)
        return obj

    def deserialize_from_file(self, file_path: str) -> T:
        with open(file_path, 'rb') as file_fp:
            return pickle.load(file_fp)

    def _is_max_age_reached(self) -> bool:
        modified_time = os.path.getmtime(self.file_path)
        age = time.time() - modified_time
        LOGGER.debug('age: %r', age)
        return age >= self.max_age_in_seconds

    def get_or_load(self, load_fn: Callable[[], T], reload: bool = False) -> T:
        with self._lock:
            if (
                not reload
                and self.file_path.exists()
                and not self._is_max_age_reached()
            ):
                return self.deserialize_from_file(str(self.file_path))
            result = load_fn()
            assert result is not None
            return self.serialize_to_file(result, str(self.file_path))

    def clear(self):
        with self._lock:
            if self.file_path.exists():
                self.file_path.unlink()
