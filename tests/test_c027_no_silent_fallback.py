"""C027 zero-result semantics: no invisible long->short fallback or fake 0."""
from __future__ import annotations

import asyncio

import pytest

from nature_video_studio.models import MediaCandidate, Rendition, SearchMode
from nature_video_studio.filtering import SearchCriteria
from nature_video_studio.search_coordinator import (
    ProviderStatus, SearchCoordinator, SearchOutcome,
)
from nature_video_studio.search_mode_state import LaneStatus, SearchModeSession
from nature_video_studio.source_adapter import SearchPage, SearchQuery


LONG, SHORT = SearchMode.LONG_ORIGINAL, SearchMode.SHORT_COMPOSER


def candidate(provider, key, seconds, *, verified=True, assembled=False):
    return MediaCandidate(
        provider=provider,
        source_id=key,
        source_url="https://example.org/fixture",
        title="Synthetic nature video",
        duration_seconds=seconds,
        original_duration_verified=verified,
        is_assembled=assembled,
        renditions=(Rendition(3840, 2160),),
        nature_relevance_verified=True,
    )


class RecordingSource:
    def __init__(self, name, modes, candidates=(), *, error=None):
        self.name = name
        self.supported_modes = frozenset(modes)
        self.candidates = tuple(candidates)
        self.error = error
        self.calls = []

    async def search(self, query):
        self.calls.append(query)
        if self.error is not None:
            raise self.error
        return SearchPage(self.name, self.candidates)


def run_search(adapters, ticket):
    return asyncio.run(SearchCoordinator(adapters).search(
        SearchQuery(ticket.text, ticket.criteria)
    ))


def test_no_silent_fallback_true_provider_zero_exposes_zero_and_alternative():
    long = RecordingSource("Internet Archive", {LONG})
    short = RecordingSource(
        "Pexels", {SHORT}, [candidate("Pexels", "20s", 20)]
    )
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "lake")
    result = run_search([long, short], ticket)
    assert session.finish_search(ticket, result)
    lane = session.lane(LONG)
    assert lane.status == LaneStatus.EMPTY
    assert lane.result_count == 0
    assert lane.results == ()
    assert "0건" in lane.status_text
    assert "짧은 영상 조합 탭 직접 열기" in lane.status_text
    assert "자동 혼합·전환·검색·다운로드 없음" in lane.status_text
    assert long.calls and long.calls[0].criteria.mode == LONG
    assert short.calls == []
    assert session.active_mode == LONG
    assert session.lane(SHORT).status == LaneStatus.NOT_SEARCHED
    assert session.lane(SHORT).result_count is None


@pytest.mark.parametrize("seconds,verified,assembled", [
    (179, True, False),
    (60, True, False),
    (None, False, False),
    (180, False, False),
    (180, True, True),
    (601, True, False),
])
def test_no_silent_fallback_all_unqualified_originals_stay_zero(
    seconds, verified, assembled,
):
    source = RecordingSource(
        "Internet Archive", {LONG},
        [candidate("Internet Archive", "bad", seconds,
                   verified=verified, assembled=assembled)],
    )
    session = SearchModeSession()
    ticket = session.begin_search(
        LONG, "lake", min_original_duration_seconds=600,
        max_original_duration_seconds=600,
    )
    outcome = run_search([source], ticket)
    assert session.finish_search(ticket, outcome)
    assert session.lane(LONG).status == LaneStatus.EMPTY
    assert session.lane(LONG).result_count == 0
    assert "10분 ~ 10분" in session.lane(LONG).status_text
    assert session.active_mode == LONG
    assert session.lane(SHORT).results == ()


def test_no_silent_fallback_accepted_long_180_never_signals_empty():
    source = RecordingSource(
        "Wikimedia Commons", {LONG}, [candidate("Wikimedia Commons", "180", 180)],
    )
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "호수")
    assert session.finish_search(ticket, run_search([source], ticket))
    assert session.lane(LONG).status == LaneStatus.RESULTS
    assert session.lane(LONG).result_count == 1
    assert session.active_mode == LONG


def test_no_silent_fallback_partial_zero_has_no_definitive_empty():
    good = RecordingSource("Wikimedia Commons", {LONG}, [])
    broken = RecordingSource("Internet Archive", {LONG}, error=RuntimeError("fixture"))
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "호수")
    assert session.finish_search(ticket, run_search([good, broken], ticket))
    lane = session.lane(LONG)
    assert lane.status == LaneStatus.PARTIAL
    assert lane.result_count == 0
    assert "0건(부분 결과)" in lane.status_text
    assert "전체 원본이 0건인지는 확인할 수 없습니다" in lane.status_text
    assert "짧은 영상 조합 탭 직접 열기" not in lane.status_text
    assert session.active_mode == LONG


def test_no_silent_fallback_partial_nonzero_preserves_long_only():
    good = RecordingSource(
        "Wikimedia Commons", {LONG}, [candidate("Wikimedia Commons", "300", 300)]
    )
    broken = RecordingSource("Internet Archive", {LONG}, error=TimeoutError("fixture"))
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "lake")
    assert session.finish_search(ticket, run_search([good, broken], ticket))
    assert session.lane(LONG).status == LaneStatus.PARTIAL
    assert session.lane(LONG).result_count == 1
    assert session.lane(SHORT).result_count is None


@pytest.mark.parametrize("cause", ["none-connected", "unsupported", "failed", "invalid"])
def test_no_silent_fallback_unavailable_and_failed_never_forge_zero(cause):
    if cause == "none-connected":
        sources = []
        expected = LaneStatus.UNAVAILABLE
    elif cause == "unsupported":
        sources = [RecordingSource("Pexels", {SHORT}, [])]
        expected = LaneStatus.UNAVAILABLE
    elif cause == "failed":
        sources = [RecordingSource("Internet Archive", {LONG}, error=TimeoutError())]
        expected = LaneStatus.FAILED
    else:
        class Malformed(RecordingSource):
            async def search(self, query):
                self.calls.append(query)
                return SearchPage("Wrong Provider", ())
        sources = [Malformed("Internet Archive", {LONG})]
        expected = LaneStatus.FAILED

    session = SearchModeSession()
    ticket = session.begin_search(LONG, "lake")
    assert session.finish_search(ticket, run_search(sources, ticket))
    lane = session.lane(LONG)
    assert lane.status == expected
    assert lane.result_count is None
    assert lane.results == ()
    assert "탭 직접 열기" not in lane.status_text
    assert session.active_mode == LONG
    assert session.lane(SHORT).status == LaneStatus.NOT_SEARCHED


def test_no_silent_fallback_unconnected_gui_state_uses_unavailable_not_empty():
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "lake")
    assert session.unavailable(ticket)
    assert session.lane(LONG).status == LaneStatus.UNAVAILABLE
    assert session.lane(LONG).result_count is None
    assert "연결되지 않았습니다" in session.lane(LONG).status_text
    assert session.active_mode == LONG


def test_no_silent_fallback_explicit_switch_only_and_no_implicit_search():
    long = RecordingSource("Internet Archive", {LONG}, [])
    short = RecordingSource(
        "Pexels", {SHORT}, [candidate("Pexels", "15s", 15)]
    )
    session = SearchModeSession()
    long_ticket = session.begin_search(LONG, "lake")
    assert session.finish_search(long_ticket, run_search([long, short], long_ticket))
    assert len(long.calls) == 1
    assert short.calls == []
    assert session.active_mode == LONG
    session.switch_to(SHORT)
    assert session.active_mode == SHORT
    assert short.calls == []  # mere tab switch never sends any search request
    assert session.lane(SHORT).result_count is None
    short_ticket = session.begin_search(SHORT, "lake clip")
    assert session.finish_search(short_ticket, run_search([long, short], short_ticket))
    assert len(short.calls) == 1
    assert session.lane(SHORT).result_count == 1
    assert session.lane(LONG).result_count == 0


def test_no_silent_fallback_long_result_zero_replaces_only_its_own_previous_results():
    session = SearchModeSession()
    first = session.begin_search(LONG, "호수")
    assert session.finish_search(first, SearchOutcome(
        accepted=(candidate("Internet Archive", "190", 190),),
        rejected={},
        providers=(ProviderStatus("Internet Archive", "OK", 1),),
    ))
    short = session.begin_search(SHORT, "해변")
    assert session.finish_search(short, SearchOutcome(
        accepted=(candidate("Pexels", "30s", 30),),
        rejected={}, providers=(ProviderStatus("Pexels", "OK", 1),),
    ))
    new = session.begin_search(LONG, "호수", min_original_duration_seconds=1800)
    assert session.finish_search(new, SearchOutcome(
        accepted=(candidate("Internet Archive", "190", 190),),
        rejected={}, providers=(ProviderStatus("Internet Archive", "OK", 1),),
    ))
    assert session.lane(LONG).status == LaneStatus.EMPTY
    assert session.lane(LONG).result_count == 0
    assert session.lane(SHORT).result_count == 1
    assert session.active_mode == LONG  # begin_search alone does not switch


def test_no_silent_fallback_stale_response_cannot_replace_new_search():
    session = SearchModeSession()
    old = session.begin_search(LONG, "lake")
    latest = session.begin_search(LONG, "lake", min_original_duration_seconds=600)
    assert not session.finish_search(old, SearchOutcome(
        accepted=(), rejected={},
        providers=(ProviderStatus("Internet Archive", "OK", 0),),
    ))
    assert session.lane(LONG).status == LaneStatus.SEARCHING
    assert session.finish_search(latest, SearchOutcome(
        accepted=(candidate("Internet Archive", "800", 800),),
        rejected={}, providers=(ProviderStatus("Internet Archive", "OK", 1),),
    ))
    assert session.lane(LONG).status == LaneStatus.RESULTS
    assert session.lane(LONG).result_count == 1


def test_no_silent_fallback_offline_demo_flag_cleared_at_next_real_request():
    session = SearchModeSession()
    session.lane(LONG).offline_zero_demo = True
    ticket = session.begin_search(LONG, "lake")
    assert session.lane(LONG).offline_zero_demo is False
    assert session.unavailable(ticket)
    assert session.lane(LONG).result_count is None
    assert "오프라인 테스트" not in session.lane(LONG).status_text


def test_no_silent_fallback_empty_short_results_do_not_turn_on_long_mode():
    session = SearchModeSession()
    session.switch_to(SHORT)
    ticket = session.begin_search(SHORT, "lake")
    assert session.finish_search(ticket, SearchOutcome(
        accepted=(), rejected={},
        providers=(ProviderStatus("Pexels", "OK", 0),),
    ))
    assert session.active_mode == SHORT
    assert session.lane(SHORT).status == LaneStatus.EMPTY
    assert "장편 결과는 섞이지 않습니다" in session.lane(SHORT).status_text
    assert session.lane(LONG).status == LaneStatus.NOT_SEARCHED
