from typing import Protocol, TypeVar


_T_co = TypeVar("_T_co", covariant=True)


# copied from typeshed
class SupportsNext(Protocol[_T_co]):
    def __next__(self) -> _T_co: ...
