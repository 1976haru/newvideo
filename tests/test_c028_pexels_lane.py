"""C028 official 5–120s Pexels clip-only provider and GUI contract.

All API adapter examples are synthetic. No requests, keys, downloads or
license approvals are performed. Official upload policy: 2026-10-04.
"""
from __future__ import annotations

import asyncio

import pytest

from nature_video_studio.filtering import SearchCriteria, duration_reason, filter_candidates
from nature_video_studio.models import MediaCandidate, Rendition, SearchMode
from nature_video_studio.provider_policy import (
    PEXELS_MIN_UPLOAD_SECONDS, PEXELS_MAX_UPLOAD_SECONDS,
    PEXELS_UPLOAD_REQUIREMENTS_URL, is_pexels,
    supports_mode, long_lane_policy_text, short_lane_policy_text,
)
from nature_video_studio.search_coordinator import SearchCoordinator
from nature_video_studio.search_mode_state import LaneStatus, SearchModeSession
from nature_video_studio.source_adapter import SearchPage, SearchQuery


LONG = SearchMode.LONG_ORIGINAL
SHORT = SearchMode.SHORT_COMPOSER


def video(provider, name, duration, *, verified=True, assembled=False):
    return MediaCandidate(
        provider=provider,
        source_id=name,
        source_url="https://www.pexels.com/video/synthetic-test/",
        title="offline synthetic landscape",
        duration_seconds=duration,
        original_duration_verified=verified,
        is_assembled=assembled,
        renditions=(Rendition(3840, 2160),),
        nature_relevance_verified=True,
    )


class Recorder:
    def __init__(self, name, supported_modes, candidates=()):
        self.name = name
        self.supported_modes = frozenset(supported_modes)
        self.candidates = tuple(candidates)
        self.calls = []

    async def search(self, query):
        self.calls.append(query.criteria.mode)
        return SearchPage(self.name, self.candidates)


def run(adapters, mode):
    return asyncio.run(SearchCoordinator(adapters).search(
        SearchQuery("호수", SearchCriteria(mode=mode))
    ))


def test_pexels_lane_policy_from_official_october_2026_upload_requirements():
    assert PEXELS_MIN_UPLOAD_SECONDS == 5
    assert PEXELS_MAX_UPLOAD_SECONDS == 120
    assert PEXELS_MAX_UPLOAD_SECONDS < 180
    assert PEXELS_UPLOAD_REQUIREMENTS_URL.endswith(
        "What-are-the-requirements-for-uploading-videos"
    )
    assert "최대 120초" in long_lane_policy_text()
    assert "장편 원본 공급처에서 제외" in long_lane_policy_text()
    assert "5~120초" in short_lane_policy_text()
    assert "제공처 미연결" in short_lane_policy_text()
    assert "상업적 재사용" in short_lane_policy_text()


@pytest.mark.parametrize("name", [
    "Pexels", "PEXELS", " pExEls ", "Pexels.com",
    "www.pexels.com", "Pexels Videos", "Pexels API",
])
def test_pexels_lane_provider_identity_is_safe_across_expected_aliases(name):
    assert is_pexels(name)
    assert not supports_mode(name, LONG, frozenset({LONG, SHORT}))
    assert supports_mode(name, SHORT, frozenset({LONG, SHORT}))
    assert not supports_mode(name, SHORT, frozenset({LONG}))


@pytest.mark.parametrize("name", ["Internet Archive", "Wikimedia Commons", "Pixabay", "", None, "My Pexels playlist"])
def test_pexels_lane_unrelated_providers_are_not_automatically_blacklisted(name):
    assert not is_pexels(name)
    if isinstance(name, str):
        assert supports_mode(name, LONG, frozenset({LONG}))
        assert not supports_mode(name, SHORT, frozenset({LONG}))


def test_pexels_lane_misconfigured_adapter_cannot_run_long_search():
    pexels = Recorder("Pexels", {LONG, SHORT}, [
        video("Pexels", "mislabelled-180", 180),
    ])
    result = run([pexels], LONG)
    assert pexels.calls == []
    assert result.accepted == ()
    assert len(result.providers) == 1
    assert result.providers[0].code == "MODE_UNSUPPORTED"
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "lake")
    assert session.finish_search(ticket, result)
    assert session.lane(LONG).status == LaneStatus.UNAVAILABLE
    assert session.lane(LONG).result_count is None


def test_pexels_lane_long_provider_mixed_with_eligible_long_provider():
    pexels = Recorder("Pexels", {LONG, SHORT}, [
        video("Pexels", "bad-400", 400),
    ])
    archive = Recorder("Internet Archive", {LONG}, [
        video("Internet Archive", "verified-600", 600)
    ])
    result = run([pexels, archive], LONG)
    assert pexels.calls == []
    assert archive.calls == [LONG]
    assert [x.provider for x in result.accepted] == ["Internet Archive"]
    assert {x.provider:x.code for x in result.providers} == {
        "Pexels":"MODE_UNSUPPORTED", "Internet Archive":"OK"
    }


@pytest.mark.parametrize("duration", [180, 180.0, 180.01, 600, 1200, 1800, 10000])
@pytest.mark.parametrize("provider", ["Pexels", "PEXELS"])
def test_pexels_lane_fake_long_duration_cannot_pass_filter(provider, duration):
    item = video(provider, "fake-long", duration)
    criteria = SearchCriteria(mode=LONG)
    assert "Pexels" in duration_reason(item, criteria)
    passed, rejected = filter_candidates([item], criteria)
    assert not passed
    assert any("120초" in r for r in rejected[item.key])


def test_pexels_lane_defensive_gui_state_rejects_fake_180_even_without_adapter():
    from nature_video_studio.search_coordinator import ProviderStatus, SearchOutcome
    session = SearchModeSession()
    ticket = session.begin_search(LONG, "lake")
    wrong_result = SearchOutcome(
        accepted=(video("Pexels", "180-original-claimed", 180),),
        rejected={},
        providers=(ProviderStatus("Internet Archive", "OK", 1),),
    )
    assert session.finish_search(ticket, wrong_result)
    assert session.lane(LONG).status == LaneStatus.EMPTY
    assert session.lane(LONG).result_count == 0
    assert session.lane(LONG).results == ()


@pytest.mark.parametrize("duration,accept", [
    (4.999, False), (5, True), (5.0001, True),
    (90, True), (119.999, True), (120, True),
    (120.001, False), (179, False), (180, False),
])
def test_pexels_lane_clip_length_exact_boundaries(duration, accept):
    clip = video("Pexels", "clip", duration)
    passed, _ = filter_candidates([clip], SearchCriteria(mode=SHORT))
    assert bool(passed) == accept


@pytest.mark.parametrize("duration,verified,assembled", [
    (None, False, False),
    (120, False, False),
    (120, True, True),
    (float("nan"), True, False),
])
def test_pexels_lane_clip_unknown_or_assembled_is_rejected(duration, verified, assembled):
    clip = video("Pexels", "bad", duration, verified=verified, assembled=assembled)
    passed, rejected = filter_candidates([clip], SearchCriteria(mode=SHORT))
    assert passed == []
    assert clip.key in rejected


def test_pexels_lane_short_adapter_called_only_after_explicit_short_search():
    pexels = Recorder("Pexels", {LONG, SHORT}, [
        video("Pexels", "valid-5", 5),
        video("Pexels", "valid-120", 120),
        video("Pexels", "over-120", 120.01),
    ])
    session = SearchModeSession()
    lt = session.begin_search(LONG, "lake")
    long_result = run([pexels], LONG)
    assert session.finish_search(lt, long_result)
    assert pexels.calls == []
    assert session.lane(LONG).status == LaneStatus.UNAVAILABLE
    # No fallback, no automatic switch, no clip search until user chooses.
    session.switch_to(SHORT)
    assert pexels.calls == []
    st = session.begin_search(SHORT, "lake clips")
    short_result = run([pexels], SHORT)
    assert session.finish_search(st, short_result)
    assert pexels.calls == [SHORT]
    assert {c.source_id for c in session.lane(SHORT).results} == {
        "valid-5", "valid-120"
    }
    assert session.lane(LONG).status == LaneStatus.UNAVAILABLE


def test_pexels_lane_unverified_180_does_not_become_long_or_short():
    pexels = video("Pexels", "180", 180, verified=False)
    for mode in (LONG, SHORT):
        approved, _ = filter_candidates([pexels], SearchCriteria(mode=mode))
        assert approved == []
