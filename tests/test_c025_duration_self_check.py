"""C025 exact original 180s, composite rejection, and offline GUI check data."""
from __future__ import annotations

import asyncio

import pytest

from nature_video_studio.duration_self_check import run_duration_self_check
from nature_video_studio.filtering import SearchCriteria, duration_reason, filter_candidates
from nature_video_studio.models import MediaCandidate, Rendition, SearchMode
from nature_video_studio.search_coordinator import (
    ProviderStatus, SearchCoordinator, SearchOutcome,
)
from nature_video_studio.search_mode_state import LaneStatus, SearchModeSession
from nature_video_studio.source_adapter import SearchPage, SearchQuery


def candidate(name, duration, *, verified=True, assembled=False):
    return MediaCandidate(
        provider="Wikimedia Commons", source_id=name,
        source_url="https://commons.wikimedia.org/wiki/File:test.webm",
        title="Lake landscape", duration_seconds=duration,
        original_duration_verified=verified,
        is_assembled=assembled,
        renditions=(Rendition(3840, 2160),),
        nature_relevance_verified=True,
    )


@pytest.mark.parametrize("duration,allowed", [
    (179, False),
    (179.999, False),
    (180, True),
    (180.0, True),
    (180.0001, True),
    (181, True),
    (600, True),
])
def test_c025_original_duration_exact_180_boundary(duration, allowed):
    accepted, _ = filter_candidates(
        [candidate(str(duration), duration)], SearchCriteria()
    )
    assert bool(accepted) is allowed


@pytest.mark.parametrize("duration,verified,assembled", [
    (None, False, False),
    (180, False, False),
    (180, True, True),
    (60 + 60 + 60, True, True),
    (1800, True, True),
    (float("nan"), True, False),
    (float("inf"), True, False),
    (-float("inf"), True, False),
    ("180", True, False),
])
def test_c025_unverified_invalid_and_assembled_never_pass(duration, verified, assembled):
    media = candidate("bad", duration, verified=verified, assembled=assembled)
    result, rejected = filter_candidates([media], SearchCriteria())
    assert result == []
    assert media.key in rejected


def test_c025_composition_cannot_leak_through_source_coordinator():
    class SyntheticSource:
        name = "Wikimedia Commons"
        supported_modes = frozenset({SearchMode.LONG_ORIGINAL})

        async def search(self, _):
            return SearchPage(self.name, (
                candidate("real-179", 179),
                candidate("fake-180-from-3-clips", 180, assembled=True),
                candidate("unknown-180", 180, verified=False),
                candidate("valid-180", 180),
                candidate("valid-181", 181),
            ))

    async def find():
        return await SearchCoordinator([SyntheticSource()]).search(
            SearchQuery("lake", SearchCriteria())
        )

    outcome = asyncio.run(find())
    assert [c.source_id for c in outcome.accepted] == ["valid-180", "valid-181"]
    assert set(outcome.rejected) == {
        "Wikimedia Commons:real-179",
        "Wikimedia Commons:fake-180-from-3-clips",
        "Wikimedia Commons:unknown-180",
    }
    assert "조합 영상은 연속 원본이 아님" in outcome.rejected[
        "Wikimedia Commons:fake-180-from-3-clips"
    ]


def test_c025_gui_session_double_checks_and_hides_assembled_180():
    session = SearchModeSession()
    ticket = session.begin_search(SearchMode.LONG_ORIGINAL, "호수")
    bad = candidate("three-clips", 180, assembled=True)
    outcome = SearchOutcome(
        accepted=(bad,), rejected={},
        providers=(ProviderStatus("Wikimedia Commons", "OK", 1),),
    )
    assert session.finish_search(ticket, outcome)
    assert session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.EMPTY
    assert session.lane(SearchMode.LONG_ORIGINAL).result_count == 0
    assert session.lane(SearchMode.LONG_ORIGINAL).results == ()


def test_c025_gui_session_includes_exactly_180_verified_original():
    session = SearchModeSession()
    ticket = session.begin_search(SearchMode.LONG_ORIGINAL, "lake")
    original = candidate("source-180", 180)
    assert session.finish_search(ticket, SearchOutcome(
        accepted=(original,), rejected={},
        providers=(ProviderStatus("Wikimedia Commons", "OK", 1),),
    ))
    assert session.lane(SearchMode.LONG_ORIGINAL).result_count == 1


def test_c025_self_check_runs_offline_and_all_scenarios_pass():
    rows = run_duration_self_check()
    assert len(rows) == 8
    assert all(row.passed for row in rows)
    assert any("조합" in row.label and not row.accepted for row in rows)
    assert any(row.label.startswith("180초 단일") and row.accepted for row in rows)
    assert any(row.label.startswith("길이 미확인") and not row.accepted for row in rows)


def test_c025_assembly_rejected_in_short_lane_too():
    clip = candidate("60x3", 180, assembled=True)
    assert "조합 영상은 개별 클립이 아님" in duration_reason(
        clip, SearchCriteria(mode=SearchMode.SHORT_COMPOSER)
    )
