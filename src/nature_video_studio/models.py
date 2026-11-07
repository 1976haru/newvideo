"""Provider-independent video metadata. The key distinction is original vs assembled length."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SearchMode(str, Enum):
    LONG_ORIGINAL = "long_original"
    SHORT_COMPOSER = "short_composer"


class ResolutionMode(str, Enum):
    FOUR_K_ONLY = "4k_only"
    FOUR_K_PREFERRED = "4k_preferred"
    FHD_MINIMUM = "fhd_minimum"


@dataclass(frozen=True)
class Rendition:
    width: int
    height: int
    media_url: str = ""
    fps: Optional[float] = None

    @property
    def is_4k(self) -> bool:
        return self.width >= 3840 and self.height >= 2160

    @property
    def is_fhd(self) -> bool:
        return self.width >= 1920 and self.height >= 1080


@dataclass(frozen=True)
class MediaCandidate:
    provider: str
    source_id: str
    source_url: str
    title: str
    duration_seconds: Optional[float]
    original_duration_verified: bool
    renditions: tuple[Rendition, ...] = field(default_factory=tuple)
    poster_url: str = ""
    creator: str = ""
    license_url: str = ""
    nature_relevance_verified: bool = False
    notes: str = ""
    # Explicit assembly provenance: a stitched timeline is NEVER one original
    # even if its total duration is >=180s or bad provider data sets verified=True.
    # Future adapters must set verified=False when provenance cannot be confirmed.
    is_assembled: bool = False

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.source_id}"

    @property
    def max_resolution(self) -> tuple[int, int]:
        if not self.renditions:
            return (0, 0)
        r = max(self.renditions, key=lambda a: a.width * a.height)
        return r.width, r.height
