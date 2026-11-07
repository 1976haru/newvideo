"""Authorized R1 source assembly for the actual V2 search window.

No calls or credential reads are performed until the user presses Search.
"""
from __future__ import annotations

from dataclasses import dataclass

from .commons_adapter import CommonsLongAdapter
from .pixabay_official_adapter import PixabayVideoAdapter
from .search_coordinator import SearchCoordinator


@dataclass
class LiveSources:
    coordinator: SearchCoordinator
    pixabay: PixabayVideoAdapter


def make_live_sources() -> LiveSources:
    pixabay = PixabayVideoAdapter()
    return LiveSources(
        coordinator=SearchCoordinator([CommonsLongAdapter(), pixabay]),
        pixabay=pixabay,
    )
