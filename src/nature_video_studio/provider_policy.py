"""C028 provider capability policy (metadata only; never performs a network call).

Pexels' official video upload requirement updated 2026-10-04:
at least 5 seconds and at most 2 minutes. Therefore Pexels cannot be
recommended as a source for a VERIFIED continuous >=180s original.

This is a search-lane capability restriction, not a copyright or
download permission decision. No Pexels API is connected in this build.
"""
from __future__ import annotations

from collections.abc import Collection

from .models import SearchMode

PEXELS_MIN_UPLOAD_SECONDS = 5
PEXELS_MAX_UPLOAD_SECONDS = 120
PEXELS_UPLOAD_REQUIREMENTS_URL = (
    "https://help.pexels.com/hc/en-us/articles/"
    "360042795133-What-are-the-requirements-for-uploading-videos"
)

# Exact, documented provider identities. Do not guess identity from titles,
# arbitrary user text, or loosely matched website substrings.
_PEXELS_IDENTITIES = frozenset({
    "pexels",
    "pexels.com",
    "www.pexels.com",
    "pexels videos",
    "pexels api",
})


def is_pexels(provider_name: object) -> bool:
    return (
        isinstance(provider_name, str)
        and provider_name.strip().casefold() in _PEXELS_IDENTITIES
    )


def supports_mode(
    provider_name: str,
    mode: SearchMode,
    advertised_modes: Collection[SearchMode],
) -> bool:
    """Apply official provider policy even if a future adapter is misconfigured."""
    mode = SearchMode(mode)
    if is_pexels(provider_name) and mode == SearchMode.LONG_ORIGINAL:
        return False
    return mode in advertised_modes


def long_lane_policy_text() -> str:
    return (
        "제공처 정책: Pexels는 공식 업로드 최대 120초로 "
        "3분 이상 장편 원본 공급처에서 제외합니다. "
        "긴 원본 후보는 별도 제공처에서 검증하며, 현재 실제 제공처 미연결입니다."
    )


def short_lane_policy_text() -> str:
    return (
        "제공처 정책: Pexels는 5~120초 짧은 클립 전용 후보입니다 "
        "(2026-10-04 공식 업로드 기준). "
        "현재 실제 제공처 미연결이며, 다운로드·상업적 재사용은 별도 권리 검토가 필요합니다."
    )
