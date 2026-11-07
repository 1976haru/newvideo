"""C024 tests: modes do not share searches, counts, sorts or request epochs."""
from __future__ import annotations

import asyncio

import pytest

from nature_video_studio.filtering import SearchCriteria, filter_candidates
from nature_video_studio.models import MediaCandidate, Rendition, SearchMode
from nature_video_studio.search_coordinator import (
    ProviderStatus, SearchCoordinator, SearchOutcome,
)
from nature_video_studio.search_mode_state import (
    LaneSort, LaneStatus, SearchModeSession, SORT_OPTIONS,
)
from nature_video_studio.source_adapter import SearchPage, SearchQuery


LONG = SearchMode.LONG_ORIGINAL
SHORT = SearchMode.SHORT_COMPOSER


def media(source_id, duration, provider="fixture", verified=True, w=3840, h=2160):
    return MediaCandidate(
        provider=provider, source_id=source_id,
        source_url="https://example.org/c024-test-only",
        title="호수 풍경 " + source_id, duration_seconds=duration,
        original_duration_verified=verified,
        renditions=(Rendition(w, h),), nature_relevance_verified=True,
    )


def response(items, provider="fixture", code="OK"):
    return SearchOutcome(
        accepted=tuple(items), rejected={},
        providers=(ProviderStatus(provider=provider, code=code),),
    )


def test_search_mode_isolation_independent_counts_and_queries():
    session = SearchModeSession()
    long_ticket = session.begin_search(LONG, "호수 30분")
    session.finish_search(long_ticket, response([media("l1", 300), media("l2", 900)]))
    assert session.lane(LONG).result_count == 2
    assert session.lane(SHORT).result_count is None
    session.switch_to(SHORT)
    short_ticket = session.begin_search(SHORT, "도시 산책")
    session.finish_search(short_ticket, response([media("s1", 9)]))
    assert session.lane(LONG).text == "호수 30분"
    assert session.lane(SHORT).text == "도시 산책"
    assert session.lane(LONG).result_count == 2
    assert session.lane(SHORT).result_count == 1
    session.switch_to(LONG)
    assert session.lane(LONG).result_count == 2
    assert session.lane(SHORT).result_count == 1


def test_search_mode_isolation_long_and_short_use_different_sort_defaults():
    session = SearchModeSession()
    assert SORT_OPTIONS[LONG] != SORT_OPTIONS[SHORT]
    assert session.lane(LONG).sort == LaneSort.LONG_DURATION
    assert session.lane(SHORT).sort == LaneSort.SHORT_DURATION
    tl = session.begin_search(LONG, "mountain")
    ts = session.begin_search(SHORT, "water")
    session.finish_search(tl, response([
        media("long-shorter", 180), media("long-longer", 2000)
    ]))
    session.finish_search(ts, response([
        media("short-longer", 80), media("short-shorter", 12)
    ]))
    assert [i.source_id for i in session.lane(LONG).results] == [
        "long-longer", "long-shorter"
    ]
    assert [i.source_id for i in session.lane(SHORT).results] == [
        "short-shorter", "short-longer"
    ]


def test_search_mode_isolation_sort_changes_only_one_mode():
    session = SearchModeSession()
    tl = session.begin_search(LONG, "lake")
    ts = session.begin_search(SHORT, "lake")
    session.finish_search(tl, response([media("l4k", 180), media("lfhd", 900, w=1920,h=1080)]))
    session.finish_search(ts, response([media("s4k", 90), media("sfhd", 15,w=1920,h=1080)]))
    session.set_sort(LONG, LaneSort.LONG_QUALITY)
    assert [i.source_id for i in session.lane(LONG).results] == ["l4k", "lfhd"]
    assert [i.source_id for i in session.lane(SHORT).results] == ["sfhd", "s4k"]
    session.set_sort(SHORT, LaneSort.SHORT_QUALITY)
    assert [i.source_id for i in session.lane(SHORT).results] == ["s4k", "sfhd"]
    assert session.lane(LONG).sort == LaneSort.LONG_QUALITY
    with pytest.raises(ValueError, match="not supported"):
        session.set_sort(LONG, LaneSort.SHORT_DURATION)


def test_search_mode_isolation_long_no_hits_never_fallbacks_to_short():
    session = SearchModeSession()
    sl = session.begin_search(LONG, "호수")
    # Erroneous provider results: a 60-second clip must not enter long lane.
    session.finish_search(sl, response([media("short-only", 60)]))
    lane = session.lane(LONG)
    assert lane.status == LaneStatus.EMPTY
    assert lane.result_count == 0
    assert "짧은 영상은 자동 대체하지 않습니다" in lane.status_text
    assert session.lane(SHORT).status == LaneStatus.NOT_SEARCHED


def test_search_mode_isolation_short_filters_180s_unknown_and_out_of_range():
    session = SearchModeSession()
    ticket = session.begin_search(SHORT, "호숫가")
    session.finish_search(ticket, response([
        media("4s", 4), media("5s", 5), media("120s", 120),
        media("121s", 121), media("180s", 180),
        media("unknown", 15, verified=False),
    ]))
    assert [x.source_id for x in session.lane(SHORT).results] == ["5s", "120s"]
    assert session.lane(SHORT).result_count == 2


@pytest.mark.parametrize("duration,expected_long,expected_short", [
    (None, False, False),
    (0, False, False),
    (4.99, False, False),
    (5, False, True),
    (30, False, True),
    (120, False, True),
    (120.1, False, False),
    (179, False, False),
    (180, True, False),
    (181, True, False),
    (1800, True, False),
])
def test_search_mode_isolation_duration_cutoff(duration, expected_long, expected_short):
    test_item = media("boundary", duration)
    for mode, expected in ((LONG, expected_long), (SHORT, expected_short)):
        got, _ = filter_candidates([test_item], SearchCriteria(mode=mode))
        assert bool(got) is expected


def test_search_mode_isolation_unknown_duration_never_claimed_as_180_original():
    for mode in (LONG, SHORT):
        candidate = media("unverified", 600, verified=False)
        got, rejected = filter_candidates([candidate], SearchCriteria(mode=mode))
        assert not got
        assert rejected


def test_search_mode_isolation_unavailable_is_not_fake_zero_hits():
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "눈 덮인 산")
    assert session.lane(LONG).status == LaneStatus.SEARCHING
    assert session.lane(LONG).result_count is None
    assert session.unavailable(ticket)
    assert session.lane(LONG).status == LaneStatus.UNAVAILABLE
    assert session.lane(LONG).result_count is None
    assert session.lane(SHORT).status == LaneStatus.NOT_SEARCHED


def test_search_mode_isolation_real_verified_empty_has_zero_count_only_in_target():
    session = SearchModeSession()
    ticket = session.begin_search(SHORT, "숲")
    session.finish_search(ticket, response([]))
    assert session.lane(SHORT).status == LaneStatus.EMPTY
    assert session.lane(SHORT).result_count == 0
    assert session.lane(LONG).result_count is None


def test_search_mode_isolation_all_providers_failed_does_not_report_zero():
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "겨울 산")
    session.finish_search(ticket, response([], code="PROVIDER_FAILED"))
    assert session.lane(LONG).status == LaneStatus.FAILED
    assert session.lane(LONG).result_count is None
    assert session.lane(SHORT).status == LaneStatus.NOT_SEARCHED


def test_search_mode_isolation_partial_provider_failure_shows_partial_count():
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "호수")
    outcome = SearchOutcome(
        (media("long", 185),), {},
        (ProviderStatus("fixture", "OK"), ProviderStatus("other", "PROVIDER_FAILED")),
    )
    session.finish_search(ticket, outcome)
    assert session.lane(LONG).status == LaneStatus.PARTIAL
    assert session.lane(LONG).result_count == 1
    assert "부분 결과" in session.lane(LONG).status_text


def test_search_mode_isolation_stale_async_response_cannot_replace_new_results():
    session = SearchModeSession()
    old = session.begin_search(LONG, "old")
    new = session.begin_search(LONG, "new")
    assert not session.finish_search(old, response([media("stale", 1000)]))
    assert session.finish_search(new, response([media("latest", 181)]))
    assert [c.source_id for c in session.lane(LONG).results] == ["latest"]
    assert session.lane(LONG).text == "new"


def test_search_mode_isolation_switch_keeps_other_inflight_requests():
    session = SearchModeSession()
    t = session.begin_search(LONG, "lakes")
    session.switch_to(SHORT)
    assert session.lane(LONG).status == LaneStatus.SEARCHING
    assert session.finish_search(t, response([media("record", 300)]))
    assert session.active_mode == SHORT
    assert session.lane(LONG).result_count == 1
    assert session.lane(SHORT).status == LaneStatus.NOT_SEARCHED


def test_search_mode_isolation_blank_query_does_not_corrupt_other_lane():
    session = SearchModeSession()
    first = session.begin_search(LONG, "morning")
    session.finish_search(first, response([media("long", 188)]))
    with pytest.raises(ValueError):
        session.begin_search(SHORT, " ")
    assert session.lane(LONG).result_count == 1
    assert session.lane(SHORT).status == LaneStatus.NOT_SEARCHED


class FixtureAdapter:
    def __init__(self, name, modes, samples):
        self.name = name
        self.supported_modes = frozenset(modes)
        self.samples = tuple(samples)
        self.requests = []

    async def search(self, query: SearchQuery) -> SearchPage:
        self.requests.append(query)
        await asyncio.sleep(0)
        return SearchPage(self.name, self.samples)


def test_search_mode_isolation_coordinator_only_calls_compatible_adapters():
    archive = FixtureAdapter(
        "Internet Archive", {LONG},
        [media("long", 300, "Internet Archive"),
         media("too_short", 20, "Internet Archive")],
    )
    pexels = FixtureAdapter(
        "Pexels", {SHORT}, [media("clip", 20, "Pexels")],
    )
    coordinator = SearchCoordinator([archive, pexels])
    session = SearchModeSession()
    tl = session.begin_search(LONG, "호수")
    session.finish_search(tl, asyncio.run(coordinator.search(SearchQuery(tl.text, tl.criteria))))
    ts = session.begin_search(SHORT, "숲")
    session.finish_search(ts, asyncio.run(coordinator.search(SearchQuery(ts.text, ts.criteria))))
    assert len(archive.requests) == 1
    assert len(pexels.requests) == 1
    assert archive.requests[0].criteria.mode == LONG
    assert pexels.requests[0].criteria.mode == SHORT
    assert [c.source_id for c in session.lane(LONG).results] == ["long"]
    assert [c.source_id for c in session.lane(SHORT).results] == ["clip"]
    assert session.lane(LONG).result_count == 1
    assert session.lane(SHORT).result_count == 1
