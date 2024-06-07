from typing import Iterable, Mapping, Optional, Sequence, TypeVar


K = TypeVar('K')
V = TypeVar('V')


def get_flat_mapped_values_for_mapping(
    mapping: Mapping[K, Sequence[V]],
    keys: Iterable[K]
) -> Sequence[V]:
    return [
        value
        for key in keys
        for value in mapping[key]
    ]


def get_flat_all_values_for_mapping(
    mapping: Mapping[K, Sequence[V]]
) -> Sequence[V]:
    return [
        value
        for values in mapping.values()
        for value in values
    ]


def get_flat_mapped_values_or_all_values_for_mapping(
    mapping: Mapping[K, Sequence[V]],
    keys: Optional[Iterable[K]]
) -> Sequence[V]:
    if keys:
        return get_flat_mapped_values_for_mapping(mapping, keys=keys)
    return get_flat_all_values_for_mapping(mapping)
