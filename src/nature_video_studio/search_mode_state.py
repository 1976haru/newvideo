"""C024 two independent search lanes; no Qt, API calls or filesystem access.

A lane's search text, sort, request epoch, statuses and accepted results live
entirely within that lane. Search results from another mode never overwrite it.
The default application has NO connected source adapters in C024: its GUI
must show UNAVAILABLE instead of inventing a 0-result provider search.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .filtering import SearchCriteria, duration_reason
from .models import MediaCandidate, ResolutionMode, SearchMode
from .search_coordinator import SearchOutcome


class LaneStatus(str, Enum):
    NOT_SEARCHED = "NOT_SEARCHED"
    SEARCHING = "SEARCHING"
    RESULTS = "RESULTS"
    EMPTY = "EMPTY"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class LaneSort(str, Enum):
    LONG_DURATION = "long_duration_desc"
    LONG_QUALITY = "long_4k_first"
    SHORT_DURATION = "short_duration_asc"
    SHORT_QUALITY = "short_4k_first"


SORT_OPTIONS: dict[SearchMode, tuple[LaneSort, ...]] = {
    SearchMode.LONG_ORIGINAL: (LaneSort.LONG_DURATION, LaneSort.LONG_QUALITY),
    SearchMode.SHORT_COMPOSER: (LaneSort.SHORT_DURATION, LaneSort.SHORT_QUALITY),
}

# C026. Exact second-based query values; four UI presets, independent upper bound.
LONG_DURATION_PRESETS_SECONDS = (180, 600, 1200, 1800)

SORT_LABELS = {
    LaneSort.LONG_DURATION: "원본 길이 긴 순",
    LaneSort.LONG_QUALITY: "4K·풍경 적합도 우선",
    LaneSort.SHORT_DURATION: "짧은 컷부터",
    LaneSort.SHORT_QUALITY: "4K·풍경 적합도 우선 (클립)",
}


@dataclass(frozen=True)
class SearchTicket:
    mode: SearchMode
    sequence: int
    text: str
    criteria: SearchCriteria


@dataclass
class LaneState:
    mode: SearchMode
    sort: LaneSort
    text: str = ""
    resolution: ResolutionMode = ResolutionMode.FOUR_K_PREFERRED
    min_original_duration_seconds: float = 180.0
    max_original_duration_seconds: float | None = None
    status: LaneStatus = LaneStatus.NOT_SEARCHED
    results: tuple[MediaCandidate, ...] = ()
    rejected: dict[str, tuple[str, ...]] = field(default_factory=dict)
    provider_codes: tuple[str, ...] = ()
    # C027 explicit offline UI preview: never represent synthetic emptiness as a live search.
    offline_zero_demo: bool = False
    sequence: int = 0

    @property
    def result_count(self) -> int | None:
        if self.status in (LaneStatus.NOT_SEARCHED, LaneStatus.SEARCHING, LaneStatus.UNAVAILABLE, LaneStatus.FAILED):
            return None
        return len(self.results)

    @property
    def status_text(self) -> str:
        if self.status == LaneStatus.NOT_SEARCHED:
            return "검색 전입니다. 제공처 데이터는 아직 조회하지 않았습니다."
        if self.status == LaneStatus.SEARCHING:
            return "해당 탭의 제공처에 검색 요청 중입니다."
        if self.status == LaneStatus.UNAVAILABLE:
            return "검색 제공처가 아직 연결되지 않았습니다. 결과 없음으로 간주하지 않습니다."
        if self.status == LaneStatus.FAILED:
            return "제공처 검색이 실패했습니다. 결과가 0건인지 확인할 수 없습니다."
        if self.status == LaneStatus.PARTIAL:
            if not self.results:
                return ("일부 제공처가 실패했습니다. 현재 확인된 후보는 0건(부분 결과)이지만 "
                        "전체 원본이 0건인지는 확인할 수 없습니다. 자동 대체하지 않습니다.")
            return "일부 제공처가 실패했습니다. 표시된 건수는 부분 결과입니다."
        if self.status == LaneStatus.EMPTY:
            if self.mode == SearchMode.LONG_ORIGINAL:
                minimum = f"{self.min_original_duration_seconds / 60:g}분"
                if self.max_original_duration_seconds is None:
                    span = minimum + " 이상"
                else:
                    maximum = f"{self.max_original_duration_seconds / 60:g}분"
                    span = minimum + " ~ " + maximum
                prefix = ("[C027 오프라인 테스트 — 실제 제공처 검색 아님] "
                          if self.offline_zero_demo else "")
                return (f"{prefix}선택한 조건의 검증된 {span} 연속 원본 0건. "
                        "검색어·최소 길이·최대 길이·화질을 변경해 재검색하거나 "
                        "아래 '짧은 영상 조합 탭 직접 열기'를 클릭해 선택할 수 있습니다. "
                        "짧은 영상은 자동 대체하지 않습니다. "
                        "자동 혼합·전환·검색·다운로드 없음.")
            return "확인된 5~120초 클립 없음 (0건). 장편 결과는 섞이지 않습니다."
        return "해당 탭에서 검색한 검증 후보만 표시합니다."


def _quality_key(c: MediaCandidate) -> tuple:
    return (not any(r.is_4k for r in c.renditions),
            not c.nature_relevance_verified)


def ordered_results(
    candidates: tuple[MediaCandidate, ...], choice: LaneSort
) -> tuple[MediaCandidate, ...]:
    if choice == LaneSort.LONG_DURATION:
        key = lambda c: (-(c.duration_seconds or 0), *_quality_key(c), c.key)
    elif choice == LaneSort.LONG_QUALITY:
        key = lambda c: (*_quality_key(c), -(c.duration_seconds or 0), c.key)
    elif choice == LaneSort.SHORT_DURATION:
        key = lambda c: ((c.duration_seconds or 0), *_quality_key(c), c.key)
    elif choice == LaneSort.SHORT_QUALITY:
        key = lambda c: (*_quality_key(c), (c.duration_seconds or 0), c.key)
    else:
        raise ValueError("Unsupported sort option")
    return tuple(sorted(candidates, key=key))


class SearchModeSession:
    """State transitions are made in GUI/consumer thread, not worker threads."""

    def __init__(self):
        self.active_mode = SearchMode.LONG_ORIGINAL
        self.lanes = {
            mode: LaneState(mode=mode, sort=SORT_OPTIONS[mode][0])
            for mode in SearchMode
        }

    def lane(self, mode: SearchMode) -> LaneState:
        return self.lanes[SearchMode(mode)]

    def switch_to(self, mode: SearchMode) -> LaneState:
        self.active_mode = SearchMode(mode)
        return self.lane(self.active_mode)

    def set_sort(self, mode: SearchMode, choice: LaneSort) -> LaneState:
        lane = self.lane(mode)
        if choice not in SORT_OPTIONS[mode]:
            raise ValueError("Sort choice is not supported in this search mode")
        lane.sort = choice
        lane.results = ordered_results(lane.results, choice)
        return lane

    def begin_search(
        self,
        mode: SearchMode,
        text: str,
        resolution: ResolutionMode = ResolutionMode.FOUR_K_PREFERRED,
        *,
        min_original_duration_seconds: float = 180.0,
        max_original_duration_seconds: float | None = None,
    ) -> SearchTicket:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("검색어를 입력하세요.")
        mode = SearchMode(mode)
        # Validate before changing any lane state: invalid upper bounds must
        # not erase the user's previous results or fire an adapter request.
        criteria = SearchCriteria(
            mode=mode,
            resolution=ResolutionMode(resolution),
            min_original_duration_seconds=min_original_duration_seconds,
            max_original_duration_seconds=max_original_duration_seconds,
        )
        lane = self.lane(mode)
        lane.sequence += 1
        lane.text = text.strip()
        lane.resolution = criteria.resolution
        lane.min_original_duration_seconds = criteria.min_original_duration_seconds
        lane.max_original_duration_seconds = criteria.max_original_duration_seconds
        lane.results = ()
        lane.rejected = {}
        lane.provider_codes = ()
        lane.offline_zero_demo = False
        lane.status = LaneStatus.SEARCHING
        return SearchTicket(mode, lane.sequence, lane.text, criteria)

    def _matches(self, ticket: SearchTicket) -> bool:
        lane = self.lane(ticket.mode)
        return lane.sequence == ticket.sequence and lane.text == ticket.text

    def unavailable(self, ticket: SearchTicket) -> bool:
        if not self._matches(ticket):
            return False
        self.lane(ticket.mode).status = LaneStatus.UNAVAILABLE
        return True

    def failed(self, ticket: SearchTicket) -> bool:
        if not self._matches(ticket):
            return False
        self.lane(ticket.mode).status = LaneStatus.FAILED
        return True

    def finish_search(self, ticket: SearchTicket, outcome: SearchOutcome) -> bool:
        if not self._matches(ticket):
            return False
        lane = self.lane(ticket.mode)
        status_codes = tuple(p.code for p in outcome.providers)
        lane.provider_codes = status_codes
        lane.rejected = dict(outcome.rejected)
        if not status_codes or all(code == "MODE_UNSUPPORTED" for code in status_codes):
            lane.status = LaneStatus.UNAVAILABLE
            return True
        # Re-apply this request's full min/max even for a malformed provider
        # or mocked coordinator result. Do not revert to the default 180s.
        accepted = tuple(
            c for c in outcome.accepted
            if duration_reason(c, ticket.criteria) is None
        )
        lane.results = ordered_results(accepted, lane.sort)
        ok_count = status_codes.count("OK")
        failures = any(code not in ("OK", "MODE_UNSUPPORTED") for code in status_codes)
        if not ok_count:
            lane.status = LaneStatus.FAILED if failures else LaneStatus.UNAVAILABLE
        elif failures:
            lane.status = LaneStatus.PARTIAL
        else:
            lane.status = LaneStatus.RESULTS if lane.results else LaneStatus.EMPTY
        return True

    @staticmethod
    def _matches_mode(candidate: MediaCandidate, mode: SearchMode) -> bool:
        """Legacy mode-only helper; use ticket criteria for real result filtering."""
        return duration_reason(candidate, SearchCriteria(mode=mode)) is None
