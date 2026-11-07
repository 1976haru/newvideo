"""C020 async poster boundary wrapping the existing synchronous safe fetcher."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from .preview import PreviewResult, fetch_poster


class PreviewService:
    """Poster processing is isolated from Qt's GUI event thread.

    A Qt application must call this from a worker bridge; it must NEVER
    invoke asyncio.run() synchronously in an event handler. QMediaPlayer
    playback is an independent GUI concern not claimed by this service.
    """

    def __init__(self, cache_dir: Path, fetcher: Callable = fetch_poster) -> None:
        self._cache_dir = Path(cache_dir)
        self._fetcher = fetcher

    async def poster(self, url: str, provider: str, session=None) -> PreviewResult:
        return await asyncio.to_thread(
            self._fetcher, url, provider, self._cache_dir, session
        )
