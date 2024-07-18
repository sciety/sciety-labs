from typing import AsyncIterable, AsyncIterator, Iterable, Optional, Sequence, Tuple, TypeVar

import asyncstdlib


T = TypeVar('T')


async def get_list_for_async_iterable(
    async_iterable: AsyncIterable[T]
) -> Sequence[T]:
    items = []
    async for item in async_iterable:
        items.append(item)
    return items


async def async_iter_sync_iterable(
    iterable: Iterable[T]
) -> AsyncIterator[T]:
    for item in iterable:
        yield item


async def get_first_item(iterable: AsyncIterable[T]) -> Optional[T]:
    async for first_item in asyncstdlib.itertools.islice(iterable, 1):
        return first_item
    return None


async def async_get_iterable_and_look_ahead_one(
    iterable: AsyncIterator[T]
) -> Tuple[AsyncIterator[T], Optional[T]]:
    first_item = await get_first_item(iterable)
    if first_item is None:
        return iterable, None
    return asyncstdlib.itertools.chain([first_item], iterable), first_item
