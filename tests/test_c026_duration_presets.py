"""C026 duration-preset contract: exact sec values and independently specified max.

Offline fixtures only. Live providers remain unconnected in the user trial GUI.
"""
from __future__ import annotations

import asyncio

import pytest

from nature_video_studio.filtering import SearchCriteria, duration_reason, filter_candidates
from nature_video_studio.models import MediaCandidate, Rendition, SearchMode
from nature_video_studio.search_coordinator import (
    ProviderStatus, SearchCoordinator, SearchOutcome,
)
from nature_video_studio.search_mode_state import (
    LONG_DURATION_PRESETS_SECONDS, LaneStatus, SearchModeSession,
)
from nature_video_studio.source_adapter import SearchPage, SearchQuery


LONG = SearchMode.LONG_ORIGINAL
SHORT = SearchMode.SHORT_COMPOSER


def media(name, seconds, *, verified=True, assembled=False, provider="Internet Archive"):
    return MediaCandidate(
        provider=provider,
        source_id=name,
        title="verified synthetic lake footage",
        source_url="https://archive.org/details/synthetic",
        duration_seconds=seconds,
        original_duration_verified=verified,
        is_assembled=assembled,
        nature_relevance_verified=True,
        renditions=(Rendition(3840, 2160),),
    )


def outcome(*candidates):
    return SearchOutcome(
        accepted=tuple(candidates),
        rejected={},
        providers=(ProviderStatus("Internet Archive", "OK", len(candidates)),),
    )


def test_duration_preset_exact_values_and_default():
    assert LONG_DURATION_PRESETS_SECONDS == (180, 600, 1200, 1800)
    session = SearchModeSession()
    lane = session.lane(LONG)
    assert lane.min_original_duration_seconds == 180
    assert lane.max_original_duration_seconds is None
    t = session.begin_search(LONG, "호수")
    assert t.criteria.min_original_duration_seconds == 180
    assert t.criteria.max_original_duration_seconds is None


@pytest.mark.parametrize("minimum", LONG_DURATION_PRESETS_SECONDS)
def test_duration_preset_all_four_minimums_pass_exact_seconds(minimum):
    criteria = SearchCriteria(min_original_duration_seconds=minimum)
    assert duration_reason(media("lower", minimum - 0.001), criteria) == "원본 길이 미달"
    assert duration_reason(media("at", minimum), criteria) is None
    assert duration_reason(media("higher", minimum + 0.001), criteria) is None


@pytest.mark.parametrize("minimum,maximum", [
    (180, 600),
    (180, 1200),
    (600, 1200),
    (600, 1800),
    (1200, 1800),
    (1800, 1800),
    (1800, 7200),
])
def test_duration_preset_max_is_independent_and_inclusive(minimum, maximum):
    criteria = SearchCriteria(
        min_original_duration_seconds=minimum,
        max_original_duration_seconds=maximum,
    )
    approved, rejected = filter_candidates([
        media("below", minimum - 0.01),
        media("first", minimum),
        media("last", maximum),
        media("beyond", maximum + 0.01),
    ], criteria)
    assert {a.source_id for a in approved} == {"first", "last"}
    assert "below" not in {a.source_id for a in approved}
    assert "beyond" not in {a.source_id for a in approved}
    assert len(rejected) == 2


@pytest.mark.parametrize("minimum,maximum", [
    (600, 599),
    (1200, 600),
    (1800, 1200),
    (180, 179),
])
def test_duration_preset_invalid_max_is_rejected_before_state_mutation(minimum, maximum):
    session = SearchModeSession()
    start = session.begin_search(LONG, "previous")
    assert session.finish_search(start, outcome(media("valid", 190)))
    before = session.lane(LONG)
    assert before.result_count == 1
    sequence = before.sequence
    with pytest.raises(ValueError, match="max duration"):
        session.begin_search(
            LONG, "bad range",
            min_original_duration_seconds=minimum,
            max_original_duration_seconds=maximum,
        )
    assert before.sequence == sequence
    assert before.text == "previous"
    assert before.result_count == 1
    assert before.min_original_duration_seconds == 180
    assert before.max_original_duration_seconds is None


def test_duration_preset_zero_minute_relaxation_is_disallowed():
    with pytest.raises(ValueError):
        SearchCriteria(min_original_duration_seconds=0)
    with pytest.raises(ValueError):
        SearchCriteria(min_original_duration_seconds=179.999)


def test_duration_preset_selected_max_remains_none_until_explicitly_set():
    session = SearchModeSession()
    for minimum in LONG_DURATION_PRESETS_SECONDS:
        t = session.begin_search(
            LONG, "beach",
            min_original_duration_seconds=minimum,
        )
        assert t.criteria.max_original_duration_seconds is None
        assert session.lane(LONG).min_original_duration_seconds == minimum


def test_duration_preset_unverified_assembled_and_nan_cannot_pass_long_ranges():
    criteria = SearchCriteria(min_original_duration_seconds=600,
                              max_original_duration_seconds=1800)
    candidates = [
        media("unverified", 1200, verified=False),
        media("composed", 1200, assembled=True),
        media("nan", float("nan")),
        media("valid-600", 600),
        media("valid-1800", 1800),
    ]
    passed, rejected = filter_candidates(candidates, criteria)
    assert {c.source_id for c in passed} == {"valid-600", "valid-1800"}
    assert {k.split(":")[1] for k in rejected} == {"unverified", "composed", "nan"}


def test_duration_preset_search_coordinator_transmits_full_query_and_filters():
    class RecordingSource:
        name = "Internet Archive"
        supported_modes = frozenset({LONG})

        def __init__(self):
            self.received = []

        async def search(self, query):
            self.received.append(query)
            return SearchPage(self.name, (
                media("too-short", 599.999),
                media("at-600", 600),
                media("inside", 900),
                media("at-1200", 1200),
                media("too-long", 1200.001),
            ))

    adapter = RecordingSource()
    session = SearchModeSession()
    ticket = session.begin_search(
        LONG, "lake", min_original_duration_seconds=600,
        max_original_duration_seconds=1200,
    )
    result = asyncio.run(SearchCoordinator([adapter]).search(
        SearchQuery(ticket.text, ticket.criteria)
    ))
    assert len(adapter.received) == 1
    assert adapter.received[0].criteria.min_original_duration_seconds == 600
    assert adapter.received[0].criteria.max_original_duration_seconds == 1200
    assert {c.source_id for c in result.accepted} == {"at-600", "inside", "at-1200"}
    assert session.finish_search(ticket, result)
    assert {c.source_id for c in session.lane(LONG).results} == {
        "at-600", "inside", "at-1200",
    }
    assert session.lane(LONG).result_count == 3


def test_duration_preset_gui_defensive_filter_uses_ticket_max_not_default():
    session = SearchModeSession()
    ticket = session.begin_search(
        LONG, "lake", min_original_duration_seconds=1200,
        max_original_duration_seconds=1800,
    )
    # Simulates a misbehaving provider/coordinator that neglected range filtering.
    result = outcome(
        media("too-short", 600), media("at-1200", 1200),
        media("at-1800", 1800), media("too-long", 1801),
        media("assembled", 1200, assembled=True),
    )
    assert session.finish_search(ticket, result)
    assert {v.source_id for v in session.lane(LONG).results} == {
        "at-1200", "at-1800",
    }
    assert session.lane(LONG).result_count == 2


def test_duration_preset_stale_response_from_previous_preset_does_not_replace():
    session = SearchModeSession()
    old = session.begin_search(LONG, "lake", min_original_duration_seconds=180)
    new = session.begin_search(
        LONG, "lake", min_original_duration_seconds=1800,
        max_original_duration_seconds=3600,
    )
    assert not session.finish_search(old, outcome(media("old", 180)))
    assert session.finish_search(
        new, outcome(media("good", 1900), media("bad", 1700))
    )
    assert [c.source_id for c in session.lane(LONG).results] == ["good"]
    assert session.lane(LONG).min_original_duration_seconds == 1800
    assert session.lane(LONG).max_original_duration_seconds == 3600


def test_duration_preset_short_lane_is_independent_and_unaffected_by_long_range():
    session = SearchModeSession()
    tlong = session.begin_search(
        LONG, "long", min_original_duration_seconds=1800,
        max_original_duration_seconds=2400,
    )
    tshort = session.begin_search(SHORT, "short")
    assert tshort.criteria.mode == SHORT
    assert tshort.criteria.min_original_duration_seconds == 180
    assert tshort.criteria.max_original_duration_seconds is None
    assert session.finish_search(tlong, outcome(media("long-2000", 2000)))
    assert session.lane(LONG).result_count == 1
    assert session.lane(SHORT).status == LaneStatus.SEARCHING
    assert session.lane(SHORT).min_original_duration_seconds == 180
    assert session.lane(SHORT).max_original_duration_seconds is None


def test_duration_preset_empty_results_show_chosen_range_not_default():
    session = SearchModeSession()
    t = session.begin_search(
        LONG, "lake", min_original_duration_seconds=600,
        max_original_duration_seconds=1800,
    )
    assert session.finish_search(t, outcome(media("too-short", 200)))
    lane = session.lane(LONG)
    assert lane.status == LaneStatus.EMPTY
    assert lane.result_count == 0
    assert "10분 ~ 30분" in lane.status_text
    assert "짧은 영상은 자동 대체하지 않습니다" in lane.status_text


def test_duration_preset_unconnected_provider_is_not_a_confirmed_zero_count():
    session = SearchModeSession()
    t = session.begin_search(LONG, "lake", min_original_duration_seconds=1800)
    assert session.unavailable(t)
    assert session.lane(LONG).result_count is None
    assert session.lane(LONG).status == LaneStatus.UNAVAILABLE
