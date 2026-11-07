"""C029 offline Pixabay VIDEO API response fixtures; no API keys or downloads.

Run: python -m pytest -q -k pixabay_video_fixture
The official video API response fields are duration, videos.large.width/height,
size, url and thumbnail (https://pixabay.com/api/docs/).
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from nature_video_studio.filtering import SearchCriteria, filter_candidates
from nature_video_studio.models import ResolutionMode, SearchMode, Rendition
from nature_video_studio.pixabay_video import (
    PIXABAY_API_DOCS, PIXABAY_CACHE_TTL_SECONDS, PIXABAY_VIDEO_ENDPOINT,
    PixabayPayloadError, parse_pixabay_video_response, validate_pixabay_ffprobe,
    probe_pixabay_local_file,
)
from nature_video_studio.search_coordinator import SearchCoordinator
from nature_video_studio.source_adapter import SearchQuery


def fixture_hit(duration=180, *, large_width=3840, large_height=2160):
    return {
        "id": 125,
        "pageURL": "https://pixabay.com/videos/id-125/",
        "type": "film",
        "tags": "lake, trees, water",
        "duration": duration,
        "user": "LandscapeTester",
        "videos": {
            "large": {
                "url": "https://cdn.pixabay.com/video/2026/01/01/125_large.mp4",
                "width": large_width, "height": large_height, "size": 12000000,
                "thumbnail": "https://cdn.pixabay.com/video/2026/01/01/125_large.jpg",
            },
            "medium": {
                "url": "https://cdn.pixabay.com/video/2026/01/01/125_medium.mp4",
                "width": 1920, "height": 1080, "size": 7000000,
                "thumbnail": "https://cdn.pixabay.com/video/2026/01/01/125_medium.jpg",
            },
        },
    }


def parse(hit):
    result = parse_pixabay_video_response({"hits": [hit]})
    assert result.provider == "Pixabay"
    assert len(result.candidates) == 1
    return result.candidates[0]


def allowed(candidate, mode=SearchMode.LONG_ORIGINAL, quality=ResolutionMode.FOUR_K_PREFERRED):
    accepted, rejected = filter_candidates(
        [candidate], SearchCriteria(mode=mode, resolution=quality))
    return bool(accepted), rejected


def test_pixabay_video_fixture_official_fields_are_not_assumptions():
    assert PIXABAY_API_DOCS == "https://pixabay.com/api/docs/"
    assert PIXABAY_VIDEO_ENDPOINT.endswith("/api/videos/")
    assert PIXABAY_CACHE_TTL_SECONDS == 24 * 60 * 60
    c = parse(fixture_hit())
    assert c.source_id == "125" and c.creator == "LandscapeTester"
    assert c.source_url == "https://pixabay.com/videos/id-125/"
    assert c.original_duration_verified and c.duration_seconds == 180
    assert c.is_assembled is False
    assert c.max_resolution == (3840, 2160)
    assert len(c.renditions) == 2
    assert c.poster_url.endswith("_large.jpg")
    assert "실파일 ffprobe 미확인" in c.notes
    assert "제3자 권리" in c.notes
    assert c.nature_relevance_verified is False
    assert c.license_url.endswith("/service/terms/")


@pytest.mark.parametrize("duration,long_ok,short_ok", [
    (4, False, False), (5, False, True), (120, False, True),
    (121, False, False), (179, False, False), (179.99, False, False),
    (180, True, False), (180.01, True, False),
    (181, True, False), (600, True, False), (1800, True, False),
])
def test_pixabay_video_fixture_exact_original_duration_modes(duration, long_ok, short_ok):
    c = parse(fixture_hit(duration))
    assert allowed(c)[0] == long_ok
    assert allowed(c, SearchMode.SHORT_COMPOSER)[0] == short_ok


@pytest.mark.parametrize("value", [
    None, False, True, "180", "", -1, 0, float("inf"), float("-inf"),
    float("nan"), [], {}, 0.0, 10**1000,
])
def test_pixabay_video_fixture_unverified_malformed_duration_fails_closed(value):
    c = parse(fixture_hit(value))
    assert c.duration_seconds is None
    assert c.original_duration_verified is False
    for mode in SearchMode:
        good, bad = allowed(c, mode)
        assert not good
        assert c.key in bad
        assert any("길이 미확인" in reason for reason in bad[c.key])


def test_pixabay_video_fixture_documented_large_is_not_always_4k():
    # The official docs' sample "large" file is only 1920x1080.
    c = parse(fixture_hit(180, large_width=1920, large_height=1080))
    assert c.max_resolution == (1920, 1080)
    assert not c.renditions[0].is_4k
    assert "FHD/이하" in c.notes
    assert allowed(c, quality=ResolutionMode.FOUR_K_ONLY)[0] is False
    assert allowed(c, quality=ResolutionMode.FHD_MINIMUM)[0] is True


@pytest.mark.parametrize("field,value", [
    ("url", ""), ("url", "http://cdn.pixabay.com/video/file.mp4"),
    ("url", "https://evil.com/file.mp4"),
    ("url", "https://cdn.pixabay.com.evil.com/file.mp4"),
    ("url", "https://cdn.pixabay.com@evil.com/video.mp4"),
    ("url", "https://cdn.pixabay.com/video/preview.jpg"),
    ("size", 0), ("size", None), ("size", "12000"),
    ("width", None), ("width", False), ("width", "3840"),
    ("height", 0), ("height", "2160"),
])
def test_pixabay_video_fixture_invalid_large_falls_back_but_not_4k(field, value):
    hit = fixture_hit()
    hit["videos"]["large"][field] = value
    c = parse(hit)
    assert c.max_resolution == (1920, 1080)
    assert len(c.renditions) == 1
    assert "large 사용불가" in c.notes
    assert allowed(c, quality=ResolutionMode.FOUR_K_ONLY)[0] is False
    assert allowed(c, quality=ResolutionMode.FHD_MINIMUM)[0] is True


def test_pixabay_video_fixture_empty_large_no_medium_never_advertised_4k():
    hit = fixture_hit()
    hit["videos"]["large"] = {"url": "", "width": 3840, "height": 2160, "size": 0}
    hit["videos"]["medium"] = {}
    c = parse(hit)
    assert not c.renditions
    assert allowed(c, quality=ResolutionMode.FOUR_K_ONLY)[0] is False
    assert allowed(c, quality=ResolutionMode.FHD_MINIMUM)[0] is False


@pytest.mark.parametrize("bad_url", [
    "http://pixabay.com/videos/id-125/",
    "https://evil.com/videos/id-125/",
    "https://pixabay.com.evil.com/videos/id-125/",
    "https://pixabay.com@evil.com/videos/id-125/",
    "https://pixabay.com/videos/id-125/?key=SECRET",
    "https://pixabay.com/photos/id-125/",
])
def test_pixabay_video_fixture_disallow_untrusted_source_page(bad_url):
    hit = fixture_hit()
    hit["pageURL"] = bad_url
    assert parse_pixabay_video_response({"hits": [hit]}).candidates == ()


@pytest.mark.parametrize("id_value", [None, True, 0, -1, "125"])
def test_pixabay_video_fixture_invalid_id_is_discarded(id_value):
    hit = fixture_hit()
    hit["id"] = id_value
    assert parse_pixabay_video_response({"hits": [hit]}).candidates == ()


@pytest.mark.parametrize("response", [None, {}, {"hits": None}, {"hits": "bad"}])
def test_pixabay_video_fixture_invalid_response_is_safe_error(response):
    with pytest.raises(PixabayPayloadError, match="PIXABAY_INVALID_RESPONSE"):
        parse_pixabay_video_response(response)


def test_pixabay_video_fixture_batch_retains_unknown_for_explicit_rejection():
    first = fixture_hit(179)
    second = fixture_hit(None)
    third = fixture_hit(180)
    fourth = fixture_hit(181)
    for n, hit in enumerate([first, second, third, fourth], start=1):
        hit["id"] = n
    page = parse_pixabay_video_response({"hits": [first, second, third, fourth]})
    good, bad = filter_candidates(list(page.candidates), SearchCriteria())
    assert [c.source_id for c in good] == ["4", "3"]
    assert set(bad) == {"Pixabay:1", "Pixabay:2"}


def test_pixabay_video_fixture_ffprobe_confirms_actual_file_4k_separately():
    c = parse(fixture_hit(180))
    probe = {
        "streams": [{"codec_type": "audio"}, {
            "codec_type": "video", "width": 3840, "height": 2160,
        }],
        "format": {"duration": "180.000000"},
    }
    evidence = validate_pixabay_ffprobe(c, c.renditions[0], probe)
    assert evidence.width == 3840 and evidence.height == 2160
    assert evidence.duration_matches_api
    assert evidence.reported_dimensions_match_file
    assert evidence.verified_long_original
    assert evidence.verified_4k_file


def test_pixabay_video_fixture_4k_api_but_real_file_fhd_must_not_claim_4k():
    c = parse(fixture_hit(180))
    evidence = validate_pixabay_ffprobe(c, c.renditions[0], {
        "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
        "format": {"duration": "180"},
    })
    assert not evidence.reported_dimensions_match_file
    assert not evidence.verified_4k_file
    assert evidence.verified_long_original


def test_pixabay_video_fixture_ffprobe_duration_below_180_fails_long_gate():
    c = parse(fixture_hit(180))
    evidence = validate_pixabay_ffprobe(c, c.renditions[0], {
        "streams": [{"codec_type": "video", "width": 3840, "height": 2160}],
        "format": {"duration": "179.95"},
    })
    assert not evidence.verified_long_original
    assert evidence.verified_4k_file


def test_pixabay_video_fixture_ffprobe_wrong_duration_or_corrupt_json():
    c = parse(fixture_hit(600))
    bad = validate_pixabay_ffprobe(c, c.renditions[0], {
        "streams": [{"codec_type": "video", "width": 3840, "height": 2160}],
        "format": {"duration": "120"},
    })
    assert not bad.duration_matches_api and not bad.verified_long_original
    corrupt = validate_pixabay_ffprobe(c, c.renditions[0], {
        "streams": [{"codec_type": "video", "width": True, "height": 2160}],
        "format": {"duration": "nan"},
    })
    assert corrupt.width is None and corrupt.duration_seconds is None
    assert not corrupt.verified_4k_file


def test_pixabay_video_fixture_ffprobe_refuses_other_media_or_other_rendition():
    c = parse(fixture_hit())
    with pytest.raises(PixabayPayloadError, match="SOURCE_MISMATCH"):
        validate_pixabay_ffprobe(c, Rendition(3840, 2160, media_url="fake"), {})


def test_pixabay_video_fixture_search_coordinator_respects_long_and_short_lanes():
    class FixtureAdapter:
        name = "Pixabay"
        supported_modes = frozenset(SearchMode)
        def __init__(self):
            self.requests = []
        async def search(self, query):
            self.requests.append(query.criteria.mode)
            first = fixture_hit(120)
            second = fixture_hit(180)
            first["id"] = 1
            second["id"] = 2
            return parse_pixabay_video_response({"hits": [first, second]})

    source = FixtureAdapter()
    coordinator = SearchCoordinator([source])
    long = asyncio.run(coordinator.search(SearchQuery("lake")))
    short = asyncio.run(coordinator.search(SearchQuery(
        "lake", SearchCriteria(mode=SearchMode.SHORT_COMPOSER))))
    assert [c.source_id for c in long.accepted] == ["2"]
    assert [c.source_id for c in short.accepted] == ["1"]
    assert source.requests == [SearchMode.LONG_ORIGINAL, SearchMode.SHORT_COMPOSER]


def test_pixabay_video_fixture_local_ffprobe_invokes_approved_local_mp4_only(tmp_path):
    local = tmp_path / "lake sample.mp4"
    local.write_bytes(b"synthetic only; no real video")
    called = []
    def fake_run(args, **kwargs):
        called.append((args, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "streams": [{"codec_type": "video", "width": 3840, "height": 2160}],
                "format": {"duration": "180.0"},
            }),
        )
    candidate = parse(fixture_hit(180))
    evidence = probe_pixabay_local_file(
        candidate, candidate.renditions[0], local, runner=fake_run,
    )
    assert evidence.verified_4k_file and evidence.verified_long_original
    args, kwargs = called[0]
    assert args[0] == "ffprobe" and args[-1] == str(local)
    assert kwargs["timeout"] == 20 and kwargs["capture_output"] is True
    assert "shell" not in kwargs


def test_pixabay_video_fixture_local_ffprobe_refuses_nonexistent_and_non_mp4(tmp_path):
    candidate = parse(fixture_hit())
    for file in (tmp_path / "missing.mp4", tmp_path / "untrusted.url"):
        with pytest.raises(PixabayPayloadError, match="PIXABAY_LOCAL_FILE_INVALID"):
            probe_pixabay_local_file(candidate, candidate.renditions[0], file)


def test_pixabay_video_fixture_ffprobe_error_redacts_local_paths_and_stderr(tmp_path):
    local = tmp_path / "private_name.mp4"
    local.write_bytes(b"dummy")
    candidate = parse(fixture_hit())
    def broken_runner(args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="password=SECRET")
    with pytest.raises(PixabayPayloadError, match="PIXABAY_FFPROBE_FAILED") as exc:
        probe_pixabay_local_file(candidate, candidate.renditions[0], local,
                                 runner=broken_runner)
    assert "private_name" not in str(exc.value)
    assert "SECRET" not in str(exc.value)
