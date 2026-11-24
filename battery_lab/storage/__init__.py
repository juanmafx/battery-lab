from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from battery_lab.models import BatterySample


class StorageError(Exception):
    pass


@runtime_checkable
class SampleStore(Protocol):
    def append(self, samples: Iterable[BatterySample]) -> None: ...

    def load(self) -> list[BatterySample]: ...
