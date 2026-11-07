"""Live, user-initiated Pixabay VIDEO search; no automatic download or key mutation.

Requires an existing Windows keyring entry (read-only) or an explicit
in-memory session key. Never logs a key, full URL, response or exceptions.
Pixabay rate limit and 24h in-process response cache are conservative.
"""
from __future__ import annotations

import asyncio
import json
from threading import RLock
from time import monotonic
from typing import Callable

import requests

from .models import SearchMode
from .pixabay_video import (
    PIXABAY_VIDEO_ENDPOINT, PIXABAY_CACHE_TTL_SECONDS,
    parse_pixabay_video_response,
)
from .source_adapter import SearchPage, SearchQuery

KEYRING_SERVICE = "NatureVideoStudio_2026"
# V1.0.2's username is provider; never write/change these legacy entries.
LEGACY_PROVIDER_USERNAMES = ("pixabay", "Pixabay")
PIXABAY_PAGE_SIZE = 20
MAX_API_BYTES = 2_000_000
REQUEST_SPACING_SECONDS = 2.0


class PixabayServiceError(RuntimeError):
    """Known stable provider status, no sensitive values."""
    def __init__(self, code: str):
        self.code = code if code in {
            "API_KEY_MISSING", "KEYRING_UNAVAILABLE", "KEYRING_ERROR",
            "PIXABAY_RATE_LIMIT", "PIXABAY_HTTP_ERROR",
            "PIXABAY_INVALID_RESPONSE", "PIXABAY_NETWORK_ERROR",
        } else "PIXABAY_NETWORK_ERROR"
        super().__init__(self.code)


def _read_existing_key() -> str | None:
    """Read only; keyring may be unavailable in an older V2 environment."""
    try:
        import keyring
    except ImportError:
        raise PixabayServiceError("KEYRING_UNAVAILABLE") from None
    try:
        for provider in LEGACY_PROVIDER_USERNAMES:
            value = keyring.get_password(KEYRING_SERVICE, provider)
            if isinstance(value, str) and value.strip():
                return value.strip()
    except Exception:
        raise PixabayServiceError("KEYRING_ERROR") from None
    return None


def _fetch_official(params: dict) -> dict:
    session = requests.Session()
    session.trust_env = False
    try:
        with session.get(
            PIXABAY_VIDEO_ENDPOINT,
            params=params,
            headers={
                "User-Agent": "NatureVideoStudio/2.0 (https://github.com/1976haru/newvideo)",
                "Accept": "application/json",
            },
            stream=True, allow_redirects=False, timeout=(5, 20)
        ) as response:
            if response.status_code == 429:
                raise PixabayServiceError("PIXABAY_RATE_LIMIT")
            if response.status_code != 200:
                raise PixabayServiceError("PIXABAY_HTTP_ERROR")
            if "json" not in response.headers.get("Content-Type", "").lower():
                raise PixabayServiceError("PIXABAY_INVALID_RESPONSE")
            body = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    body.extend(chunk)
                if len(body) > MAX_API_BYTES:
                    raise PixabayServiceError("PIXABAY_INVALID_RESPONSE")
            obj = json.loads(body.decode("utf-8"))
            if not isinstance(obj, dict):
                raise PixabayServiceError("PIXABAY_INVALID_RESPONSE")
            return obj
    except PixabayServiceError:
        raise
    except (requests.RequestException, ValueError, UnicodeError, OSError):
        raise PixabayServiceError("PIXABAY_NETWORK_ERROR") from None
    finally:
        session.close()


class PixabayVideoAdapter:
    name = "Pixabay"
    supported_modes = frozenset({
        SearchMode.LONG_ORIGINAL, SearchMode.SHORT_COMPOSER
    })

    def __init__(
        self,
        fetch_json: Callable[[dict], dict] | None = None,
        lookup_key: Callable[[], str | None] | None = None,
    ):
        self._fetch_json = fetch_json or _fetch_official
        self._lookup_key = lookup_key or _read_existing_key
        self._session_key: str | None = None
        self._cache: dict[tuple[str, str], tuple[float, SearchPage]] = {}
        self._lock = RLock()
        self._next_allowed = 0.0

    def set_session_key(self, key: str) -> bool:
        """Never writes registry, files, logs or inherited V1 key entries."""
        if not isinstance(key, str) or not (10 <= len(key.strip()) <= 512):
            return False
        with self._lock:
            self._session_key = key.strip()
            self._cache.clear()
        return True

    def _key(self) -> str:
        with self._lock:
            key = self._session_key
        if key:
            return key
        value = self._lookup_key()
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise PixabayServiceError("API_KEY_MISSING")

    def _search_sync(self, query: SearchQuery) -> SearchPage:
        keyword = query.text.strip()
        if not keyword or len(keyword) > 100 or any(ord(c) < 32 for c in keyword):
            raise PixabayServiceError("PIXABAY_INVALID_RESPONSE")
        key = self._key()  # This runs exclusively in the worker thread.
        import hashlib
        key_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
        cache_id = (key_id, keyword.casefold())
        with self._lock:
            saved = self._cache.get(cache_id)
            if saved and monotonic() - saved[0] < PIXABAY_CACHE_TTL_SECONDS:
                return saved[1]
            if monotonic() < self._next_allowed:
                raise PixabayServiceError("PIXABAY_RATE_LIMIT")
            self._next_allowed = monotonic() + REQUEST_SPACING_SECONDS
        params = {
            "key": key, "q": keyword, "video_type": "film", "safesearch": "true",
            "per_page": PIXABAY_PAGE_SIZE, "page": 1, "lang": "ko",
        }
        try:
            page = parse_pixabay_video_response(self._fetch_json(params))
        except PixabayServiceError:
            raise
        except Exception:
            raise PixabayServiceError("PIXABAY_INVALID_RESPONSE") from None
        with self._lock:
            self._cache[cache_id] = (monotonic(), page)
            # Bounded in-memory cache, no secret or API response persisted.
            if len(self._cache) > 100:
                oldest = min(self._cache, key=lambda k: self._cache[k][0])
                del self._cache[oldest]
        return page

    async def search(self, query: SearchQuery) -> SearchPage:
        return await asyncio.to_thread(self._search_sync, query)
