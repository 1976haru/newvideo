"""C020 composition port only; no misleading video export or ffmpeg calls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .service_errors import FeatureUnavailable

ALLOWED_OUTPUT_MINUTES = frozenset({3, 10, 20, 30, 60})


@dataclass(frozen=True)
class CompositionPlan:
    asset_keys: tuple[str, ...]
    target_minutes: int

    def __post_init__(self):
        if self.target_minutes not in ALLOWED_OUTPUT_MINUTES:
            raise ValueError("Unsupported output duration")
        if not self.asset_keys or any(not key for key in self.asset_keys):
            raise ValueError("Composition requires selected sources")


class Composer(Protocol):
    """A future implementation must inspect real files and rights first."""
    async def render(self, plan: CompositionPlan) -> str:
        ...


class UnavailableComposer:
    async def render(self, plan: CompositionPlan) -> str:
        raise FeatureUnavailable("C020: composer backend not implemented")
