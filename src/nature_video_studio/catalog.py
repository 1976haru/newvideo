"""C020 V2 catalog boundary; explicitly excludes legacy V1 SQLite writes."""
from __future__ import annotations

from typing import Protocol

from .models import MediaCandidate
from .service_errors import FeatureUnavailable


class Catalog(Protocol):
    """Only future V2 data-root implementations may write the catalog."""
    async def find(self, source_key: str) -> MediaCandidate | None:
        ...

    async def record(self, asset: MediaCandidate) -> None:
        ...


class UnavailableCatalog:
    async def find(self, source_key: str) -> MediaCandidate | None:
        raise FeatureUnavailable("C020: V2 catalog backend not implemented")

    async def record(self, asset: MediaCandidate) -> None:
        raise FeatureUnavailable("C020: V2 catalog backend not implemented")
