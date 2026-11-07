"""Conservative copyright evidence triage; not legal clearance."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class RightsState(str, Enum):
    GENERAL_REVIEW = "general_review"
    ATTRIBUTION_REVIEW = "attribution_review"
    BLOCKED = "blocked"
    USER_VERIFIED = "user_verified"


@dataclass(frozen=True)
class RightsDecision:
    status: RightsState
    reason: str
    attribution_required: bool

    @property
    def can_auto_download(self) -> bool:
        # A source's blanket content license is not permission to ignore third-party rights.
        return self.status == RightsState.USER_VERIFIED


def license_triage(url: str, provider: str = "") -> RightsDecision:
    p = urlparse((url or "").strip())
    if p.scheme not in ("https", "http") or not p.hostname:
        return RightsDecision(RightsState.BLOCKED, "라이선스 URL 미확인", False)
    host = p.hostname.lower().removeprefix("www.")
    path = p.path.lower().rstrip("/")
    if host == "creativecommons.org":
        if path in ("/publicdomain/zero/1.0", "/publicdomain/mark/1.0"):
            return RightsDecision(RightsState.GENERAL_REVIEW, "CC0/PD 표시: 권리자 및 제3자 권리 확인 필요", False)
        if path.startswith("/licenses/by-nc") or path.startswith("/licenses/by-nd") or path.startswith("/licenses/by-nc-nd") or path.startswith("/licenses/by-nc-sa"):
            return RightsDecision(RightsState.BLOCKED, "NC/ND 계열: 상업 플레이리스트 이용에 부적합 또는 추가 조건", False)
        if path in ("/licenses/by/4.0", "/licenses/by/3.0", "/licenses/by-sa/4.0", "/licenses/by-sa/3.0"):
            return RightsDecision(RightsState.ATTRIBUTION_REVIEW, "저작자·출처·변경사항·동일조건변경허락 여부 수동 검토", True)
        return RightsDecision(RightsState.BLOCKED, "지원하지 않는 Creative Commons 버전/조건", False)
    if provider == "Pexels" and host == "pexels.com" and path == "/license":
        return RightsDecision(RightsState.GENERAL_REVIEW, "Pexels 일반 라이선스; 제3자 권리 검토 필요", False)
    if provider == "Pixabay" and host == "pixabay.com" and path in ("/service/license-summary", "/service/terms"):
        return RightsDecision(RightsState.GENERAL_REVIEW, "Pixabay 일반 라이선스; 제3자 권리 검토 필요", False)
    return RightsDecision(RightsState.BLOCKED, "공식 라이선스로 확인되지 않은 URL", False)
