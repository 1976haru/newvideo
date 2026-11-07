"""C030 deterministic Commons videoinfo + extmetadata adapter fixture gates."""
from __future__ import annotations

import asyncio
import threading
from copy import deepcopy

import pytest

from nature_video_studio.commons_adapter import (
    COMMONS_API, CommonsAdapterError, CommonsLongAdapter,
    commons_video_candidate, parse_commons_response,
)
from nature_video_studio.filtering import SearchCriteria
from nature_video_studio.models import SearchMode, ResolutionMode
from nature_video_studio.rights import RightsState, license_triage
from nature_video_studio.search_coordinator import SearchCoordinator
from nature_video_studio.source_adapter import SearchQuery


def file_page(*, name="Lake_scene.webm", duration=181, mime="video/webm",
              width=3840, height=2160, license_url="https://creativecommons.org/licenses/by/4.0/"):
    metadata = ([] if duration is None else [
        {"name": "playtime_seconds" if mime == "video/webm" else "length",
         "value": duration}
    ])
    return {
        "pageid": 12345, "ns": 6, "title": "File:" + name,
        "videoinfo": [{
            "mediatype": "VIDEO", "mime": mime,
            "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/" + name,
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:" + name,
            "size": 4_200_000, "width": width, "height": height,
            "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/" + name + "/320px-file.jpg",
            "user": "Uploader",
            "metadata": metadata,
            "extmetadata": {
                "Artist": {"value": "<b>Scenery Author</b>"},
                "LicenseShortName": {"value": "CC BY 4.0"},
                "LicenseUrl": {"value": license_url},
                "UsageTerms": {"value": "<i>Attribution required</i>"},
            },
        }],
    }


def api_response(*pages, offset=None):
    result = {"query": {"pages": list(pages)}}
    if offset:
        result["continue"] = {"continue": "-||", "gsroffset": offset}
    return result


def test_commons_adapter_uses_exact_official_api_fields_and_safe_rights():
    c = commons_video_candidate(file_page())
    assert c is not None
    assert c.provider == "Wikimedia Commons"
    assert c.duration_seconds == 181 and c.original_duration_verified
    assert c.is_assembled is False
    assert c.max_resolution == (3840, 2160)
    assert c.renditions[0].media_url.startswith("https://upload.wikimedia.org/")
    assert c.creator == "Scenery Author"
    assert c.source_url.startswith("https://commons.wikimedia.org/wiki/File:")
    assert c.license_url.endswith("/by/4.0/")
    assert not c.nature_relevance_verified
    assert "실파일 ffprobe" in c.notes
    rights = license_triage(c.license_url, c.provider)
    assert rights.status == RightsState.ATTRIBUTION_REVIEW
    assert not rights.can_auto_download


@pytest.mark.parametrize("duration,expected", [
    (179, False), (179.999, False), (180, True), (180.0, True),
    (181, True), (600, True), (1800, True),
    (None, False), (0, False), (-1, False), ("unknown", False),
    ("180", True), (float("nan"), False), (float("inf"), False),
])
def test_commons_adapter_duration_floor_is_verified_metadata_only(duration, expected):
    payload = api_response(file_page(duration=duration))
    coordinator = SearchCoordinator([CommonsLongAdapter(lambda p: payload)])
    result = asyncio.run(coordinator.search(SearchQuery("lake")))
    assert bool(result.accepted) == expected


def test_commons_adapter_ogg_length_metadata_and_source_file():
    c = commons_video_candidate(file_page(
        name="Quiet_lake.ogv", mime="video/ogg", duration="185.5"
    ))
    assert c.duration_seconds == 185.5
    assert c.original_duration_verified


def test_commons_adapter_unknown_duration_rejected_even_4k():
    p = file_page(duration=None)
    p["title"] = "File:Ten minutes beautiful lake.webm"
    c = commons_video_candidate(p)
    assert c.duration_seconds is None and not c.original_duration_verified
    outcome = asyncio.run(SearchCoordinator([CommonsLongAdapter(
        lambda params: api_response(p)
    )]).search(SearchQuery("lake")))
    assert not outcome.accepted
    assert outcome.rejected


def test_commons_adapter_conflicting_duration_metadata_is_unknown():
    p = file_page(duration=180)
    p["videoinfo"][0]["metadata"].append({"name": "length", "value": 15})
    c = commons_video_candidate(p)
    assert not c.original_duration_verified


@pytest.mark.parametrize("kind", ["BITMAP", "AUDIO", "MULTIMEDIA", "UNKNOWN"])
def test_commons_adapter_non_video_excluded(kind):
    p = file_page()
    p["videoinfo"][0]["mediatype"] = kind
    assert commons_video_candidate(p) is None


@pytest.mark.parametrize("wrong_url", [
    "http://upload.wikimedia.org/a.webm",
    "https://evil.com/a.webm",
    "https://upload.wikimedia.org.evil.com/a.webm",
    "https://upload.wikimedia.org@evil.com/a.webm",
    "https://localhost/a.webm",
])
def test_commons_adapter_external_or_unsafe_media_url_excluded(wrong_url):
    p = file_page()
    p["videoinfo"][0]["url"] = wrong_url
    assert commons_video_candidate(p) is None


@pytest.mark.parametrize("license_url,state", [
    ("https://creativecommons.org/licenses/by/4.0/", RightsState.ATTRIBUTION_REVIEW),
    ("https://creativecommons.org/licenses/by-sa/4.0/", RightsState.ATTRIBUTION_REVIEW),
    ("https://creativecommons.org/licenses/by-nc/4.0/", RightsState.BLOCKED),
    ("https://creativecommons.org/licenses/by-nd/4.0/", RightsState.BLOCKED),
    ("https://example.net/license", RightsState.BLOCKED),
    ("", RightsState.BLOCKED),
])
def test_commons_adapter_rights_review_is_never_auto_download(license_url, state):
    candidate = commons_video_candidate(file_page(license_url=license_url))
    assert candidate is not None
    triage = license_triage(candidate.license_url, candidate.provider)
    assert triage.status == state
    assert not triage.can_auto_download


def test_commons_adapter_pages_and_pagination():
    p = file_page()
    result = parse_commons_response(api_response(p, offset=15))
    assert len(result.candidates) == 1
    assert result.next_cursor == "15"


@pytest.mark.parametrize("bad", [None, {}, {"error": {"code": "maxlag"}},
                                  {"query": {"pages": {}}}])
def test_commons_adapter_invalid_response_does_not_claim_zero(bad):
    with pytest.raises(CommonsAdapterError, match="COMMONS_INVALID_RESPONSE"):
        parse_commons_response(bad)


def test_commons_adapter_only_long_mode_runs_and_separates_short():
    captures = []
    def fetch(params):
        captures.append(params)
        return api_response(file_page())
    adapter = CommonsLongAdapter(fetch)
    manager = SearchCoordinator([adapter])
    long = asyncio.run(manager.search(SearchQuery("lake")))
    short = asyncio.run(manager.search(SearchQuery(
        "lake", SearchCriteria(mode=SearchMode.SHORT_COMPOSER))))
    assert [x.source_id for x in long.accepted] == ["File:Lake_scene.webm"]
    assert not short.accepted and short.providers[0].code == "MODE_UNSUPPORTED"
    assert len(captures) == 1
    params = captures[0]
    assert params["prop"] == "videoinfo" and "imageinfo" not in params["prop"]
    assert "extmetadata" in params["viprop"]
    assert params["gsrnamespace"] == "6"
    assert params["gsrlimit"] == "5"
    assert params["maxlag"] == "5"
    assert params["gsrsearch"] == "filetype:video lake"


def test_commons_adapter_network_fetch_is_off_calling_event_loop_thread():
    calling_thread = threading.get_ident()
    seen = []
    def fetch(params):
        seen.append(threading.get_ident())
        return api_response(file_page())
    adapter = CommonsLongAdapter(fetch)
    result = asyncio.run(adapter.search(SearchQuery("lake")))
    assert seen and seen[0] != calling_thread
    assert result.candidates


@pytest.mark.parametrize("cursor", ["not a number", "-1", "1001", "999999", ""])
def test_commons_adapter_malformed_cursor_does_not_call_api(cursor):
    called = []
    adapter = CommonsLongAdapter(lambda p: called.append(p) or api_response())
    with pytest.raises(CommonsAdapterError, match="COMMONS_INVALID_CURSOR"):
        asyncio.run(adapter.search(SearchQuery("lake", cursor=cursor)))
    assert not called


def test_commons_adapter_pagination_cursor_official_param():
    calls = []
    adapter = CommonsLongAdapter(lambda p: calls.append(p) or api_response())
    asyncio.run(adapter.search(SearchQuery("호수", cursor="25")))
    assert calls[0]["gsroffset"] == "25"


def test_commons_adapter_4k_only_requires_actual_rendition_dimensions():
    adapter = CommonsLongAdapter(lambda p: api_response(file_page(width=1920, height=1080)))
    result = asyncio.run(SearchCoordinator([adapter]).search(
        SearchQuery("lake", SearchCriteria(resolution=ResolutionMode.FOUR_K_ONLY))))
    assert not result.accepted
    assert result.rejected["Wikimedia Commons:File:Lake_scene.webm"]


def test_commons_adapter_unrelated_api_failures_do_not_leak_raw_secret():
    def broken(_params):
        raise RuntimeError("token=SECRET")
    manager = SearchCoordinator([CommonsLongAdapter(broken)])
    result = asyncio.run(manager.search(SearchQuery("lake")))
    assert result.providers[0].code == "PROVIDER_FAILED"
    assert "SECRET" not in repr(result)
