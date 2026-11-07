"""C020 download queue port: NO download backend is implemented here."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .rights import RightsDecision
from .network_security import require_download_url
from .service_errors import FeatureUnavailable


@dataclass(frozen=True)
class DownloadIntent:
    source_key: str
    user_selected: bool
    rights: RightsDecision
    source_url: str | None = None
    provider: str | None = None

    def __post_init__(self):
        # Keys are provider:source-id identifiers, NEVER raw or signed URLs.
        # Error text must not contain source identifiers or secrets.
        if (
            not isinstance(self.source_key, str)
            or len(self.source_key) > 256
            or ":" not in self.source_key
            or any(c in self.source_key for c in "/\\?#@=\r\n")
            or not self.user_selected
        ):
            raise ValueError("Download requires an explicitly selected source")
        if not isinstance(self.rights, RightsDecision) or not self.rights.can_auto_download:
            raise ValueError("Download requires completed rights verification")
        # Optional until an R3 concrete backend is implemented. Future live
        # backend MUST require a validated URL and repeat verification.
        if (self.source_url is None) != (self.provider is None):
            raise ValueError("Download source URL and provider must be provided together")
        if self.source_url is not None:
            require_download_url(self.source_url, self.provider)


class DownloadQueue(Protocol):
    """Real backend must revalidate selection, rights, host and redirect."""
    async def enqueue(self, intent: DownloadIntent) -> str:
        ...


class UnavailableDownloadQueue:
    async def enqueue(self, intent: DownloadIntent) -> str:
        raise FeatureUnavailable("C020: download backend not implemented")
