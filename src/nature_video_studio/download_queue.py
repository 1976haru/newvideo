"""C020 download queue port: NO download backend is implemented here."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .rights import RightsDecision
from .service_errors import FeatureUnavailable


@dataclass(frozen=True)
class DownloadIntent:
    source_key: str
    user_selected: bool
    rights: RightsDecision

    def __post_init__(self):
        if not self.source_key or not self.user_selected:
            raise ValueError("Download requires an explicitly selected source")
        if not isinstance(self.rights, RightsDecision) or not self.rights.can_auto_download:
            raise ValueError("Download requires completed rights verification")


class DownloadQueue(Protocol):
    """Real backend must revalidate selection, rights, host and redirect."""
    async def enqueue(self, intent: DownloadIntent) -> str:
        ...


class UnavailableDownloadQueue:
    async def enqueue(self, intent: DownloadIntent) -> str:
        raise FeatureUnavailable("C020: download backend not implemented")
