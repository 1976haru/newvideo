"""C020 official-source adapter boundary; no concrete network provider here."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .filtering import SearchCriteria
from .models import MediaCandidate, SearchMode


@dataclass(frozen=True)
class SearchQuery:
    """User query/criteria; never silently replace long originals with clips."""
    text: str
    criteria: SearchCriteria = field(default_factory=SearchCriteria)
    cursor: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("Search query text must not be blank")
        if self.cursor is not None and (
            not isinstance(self.cursor, str) or len(self.cursor) > 2048
        ):
            raise ValueError("Invalid provider cursor")


@dataclass(frozen=True)
class SearchPage:
    provider: str
    candidates: tuple[MediaCandidate, ...] = ()
    next_cursor: str | None = None


class SourceAdapter(Protocol):
    """Each concrete provider implements its own authorized requests and limits.

    Implementations MUST be async, respect quotas/Retry-After and never
    substitute short clips for a long-original request. No adapters are wired
    to this contract in C020; that work belongs to R1.
    """
    name: str
    supported_modes: frozenset[SearchMode]

    async def search(self, query: SearchQuery) -> SearchPage:
        ...
