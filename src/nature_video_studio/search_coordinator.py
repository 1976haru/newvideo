"""C020 headless multi-source orchestration; no GUI, HTTP, keyring, or DB imports."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

from .filtering import filter_candidates
from .models import MediaCandidate
from .source_adapter import SearchPage, SearchQuery, SourceAdapter
from .provider_policy import supports_mode


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    code: str
    returned_count: int = 0


@dataclass(frozen=True)
class SearchOutcome:
    accepted: tuple[MediaCandidate, ...]
    rejected: dict[str, tuple[str, ...]]
    providers: tuple[ProviderStatus, ...]


class SearchCoordinator:
    """Run injected async adapters independently, then apply strict filtering.

    This coroutine is for an application worker/event-loop integration,
    NEVER a synchronous call on the Qt GUI thread. Individual providers
    own network retries; no concrete provider is available in C020.
    """

    def __init__(self, adapters: Iterable[SourceAdapter]) -> None:
        self._adapters = tuple(adapters)
        names = [adapter.name for adapter in self._adapters]
        if any(not isinstance(n, str) or not n.strip() for n in names):
            raise ValueError("Source provider names must not be blank")
        if len(names) != len(set(names)):
            raise ValueError("Duplicate source adapter name")

    @staticmethod
    async def _call(adapter: SourceAdapter, query: SearchQuery):
        try:
            page = await adapter.search(query)
            if not isinstance(page, SearchPage) or page.provider != adapter.name:
                return None, ProviderStatus(adapter.name, "INVALID_PROVIDER_RESULT")
            if any(c.provider != adapter.name for c in page.candidates):
                return None, ProviderStatus(adapter.name, "INVALID_PROVIDER_RESULT")
            return page, ProviderStatus(adapter.name, "OK", len(page.candidates))
        except Exception:
            # Never print exception: may contain API keys, URLs and response bodies.
            # asyncio.CancelledError is BaseException and is deliberately propagated.
            return None, ProviderStatus(adapter.name, "PROVIDER_FAILED")

    async def search(self, query: SearchQuery) -> SearchOutcome:
        compatible = [
            adapter for adapter in self._adapters
            if supports_mode(adapter.name, query.criteria.mode, adapter.supported_modes)
        ]
        incompatible = [
            ProviderStatus(adapter.name, "MODE_UNSUPPORTED")
            for adapter in self._adapters
            if not supports_mode(adapter.name, query.criteria.mode, adapter.supported_modes)
        ]
        replies = await asyncio.gather(*(self._call(a, query) for a in compatible))
        all_candidates = [candidate for page, _ in replies if page is not None
                          for candidate in page.candidates]
        accepted, rejected = filter_candidates(all_candidates, query.criteria)
        statuses = [status for _, status in replies] + incompatible
        order = {adapter.name: idx for idx, adapter in enumerate(self._adapters)}
        statuses.sort(key=lambda item: order[item.provider])
        return SearchOutcome(
            accepted=tuple(accepted),
            rejected={key: tuple(value) for key, value in rejected.items()},
            providers=tuple(statuses),
        )
