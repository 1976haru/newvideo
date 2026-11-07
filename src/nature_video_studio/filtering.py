"""Strict original duration rules; no silent fallback from long original to montage."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
import math

from .models import MediaCandidate, ResolutionMode, SearchMode


@dataclass(frozen=True)
class SearchCriteria:
    mode: SearchMode = SearchMode.LONG_ORIGINAL
    min_original_duration_seconds: float = 180.0
    max_original_duration_seconds: float | None = None
    resolution: ResolutionMode = ResolutionMode.FOUR_K_PREFERRED

    def __post_init__(self) -> None:
        # Never let client-supplied criteria relax the 180-second LONG floor.
        if not _finite_duration(self.min_original_duration_seconds) or self.min_original_duration_seconds < 180:
            raise ValueError("long-original minimum must be a finite number >= 180")
        if self.max_original_duration_seconds is not None:
            if not _finite_duration(self.max_original_duration_seconds):
                raise ValueError("max duration must be finite")
            if self.max_original_duration_seconds < self.min_original_duration_seconds:
                raise ValueError("max duration must be >= min duration")


def _finite_duration(value: object) -> bool:
    """Reject NaN/inf, strings, booleans and malformed provider numbers."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(value)
    except (TypeError, ValueError, OverflowError):
        return False


def duration_reason(candidate: MediaCandidate, criteria: SearchCriteria) -> str | None:
    if criteria.mode == SearchMode.LONG_ORIGINAL:
        if candidate.is_assembled:
            return "조합 영상은 연속 원본이 아님"
        if not candidate.original_duration_verified or not _finite_duration(candidate.duration_seconds):
            return "원본 길이 미확인"
        if candidate.duration_seconds < criteria.min_original_duration_seconds:
            return "원본 길이 미달"
        if criteria.max_original_duration_seconds is not None and candidate.duration_seconds > criteria.max_original_duration_seconds:
            return "원본 길이 초과"
        return None
    if criteria.mode == SearchMode.SHORT_COMPOSER:
        if candidate.is_assembled:
            return "조합 영상은 개별 클립이 아님"
        if not candidate.original_duration_verified or not _finite_duration(candidate.duration_seconds):
            return "클립 길이 미확인"
        if candidate.duration_seconds <= 0:
            return "비정상적 길이"
        if candidate.duration_seconds < 5:
            return "클립 길이 미달 (5초 미만)"
        if candidate.duration_seconds > 120:
            return "클립 길이 초과 (120초 초과)"
        return None
    return "잘못된 검색 모드"


def resolution_reason(candidate: MediaCandidate, criteria: SearchCriteria) -> str | None:
    renditions = candidate.renditions
    if not renditions:
        return "해상도 정보 없음"
    if criteria.resolution == ResolutionMode.FOUR_K_ONLY and not any(r.is_4k for r in renditions):
        return "4K 원본 파일 없음"
    if criteria.resolution == ResolutionMode.FHD_MINIMUM and not any(r.is_fhd for r in renditions):
        return "FHD 이상 파일 없음"
    # In 4K preferred, return FHD variants but present ACTUAL resolution.
    return None


def reject_reasons(candidate: MediaCandidate, criteria: SearchCriteria) -> list[str]:
    reasons = [duration_reason(candidate, criteria), resolution_reason(candidate, criteria)]
    return [reason for reason in reasons if reason]


def filter_candidates(candidates: list[MediaCandidate], criteria: SearchCriteria) -> tuple[list[MediaCandidate], dict[str, list[str]]]:
    accepted: list[MediaCandidate] = []
    rejected: dict[str, list[str]] = {}
    for video in candidates:
        reasons = reject_reasons(video, criteria)
        if reasons:
            rejected[video.key] = reasons
        else:
            accepted.append(video)
    accepted.sort(key=lambda v: (
        not any(r.is_4k for r in v.renditions),
        not v.nature_relevance_verified,
        -(v.duration_seconds or 0),
        v.key,
    ))
    return accepted, rejected
