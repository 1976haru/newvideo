"""C025 deterministic local duration-policy check (no network, user files or keys).

Synthetic fixtures demonstrate the currently deployed filter. This is not
source authentication and does not prove a provider's real-world media length.
"""
from __future__ import annotations

from dataclasses import dataclass

from .filtering import SearchCriteria, filter_candidates
from .models import MediaCandidate, Rendition


@dataclass(frozen=True)
class DurationSelfCheckResult:
    label: str
    accepted: bool
    expected: bool

    @property
    def passed(self) -> bool:
        return self.accepted == self.expected


def run_duration_self_check() -> tuple[DurationSelfCheckResult, ...]:
    """Verify exclusions and exact 180-second boundary using the live filter."""
    cases = (
        ("179초 단일 원본", 179, True, False, False),
        ("179.999초 단일 원본", 179.999, True, False, False),
        ("180초 단일 원본", 180, True, False, True),
        ("181초 단일 원본", 181, True, False, True),
        ("길이 미확인", None, False, False, False),
        ("180초 원본 검증 안 됨", 180, False, False, False),
        ("60초 × 3개 = 180초 조합", 180, True, True, False),
        ("NaN 길이 (잘못된 수치)", float("nan"), True, False, False),
    )
    checks: list[DurationSelfCheckResult] = []
    for idx, (label, duration, verified, assembled, expected) in enumerate(cases):
        candidate = MediaCandidate(
            provider="C025_OFFLINE_TEST_ONLY",
            source_id=str(idx),
            source_url="",
            title=label,
            duration_seconds=duration,
            original_duration_verified=verified,
            is_assembled=assembled,
            renditions=(Rendition(3840, 2160),),
            nature_relevance_verified=True,
        )
        accepted, _ = filter_candidates([candidate], SearchCriteria())
        checks.append(DurationSelfCheckResult(label, bool(accepted), expected))
    return tuple(checks)
