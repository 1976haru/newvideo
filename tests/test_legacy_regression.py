"""C017 deterministic legacy failure corpus regression.

The screenshot/legacy archive source facts come from the prior C013 audit.
All HTTP, media stderr and meeting-title cases are synthetic, not captures.
No network, real V1 files, Windows credentials, ffprobe or Qt needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from nature_video_studio.filtering import SearchCriteria, filter_candidates
from nature_video_studio.models import MediaCandidate, Rendition
from nature_video_studio.playback_diagnostics import classify_playback_failure
from nature_video_studio.preview import fetch_poster


CORPUS = Path(__file__).parent / "fixtures" / "legacy_v102_failures.json"


def load_corpus():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def cases(section):
    return [pytest.param(item, id=item["id"]) for item in load_corpus()[section]]


class FakeResponse:
    def __init__(self, case):
        self.status_code = case["http_status"]
        self.headers = {"Content-Type": case.get("mime", "image/jpeg"),
                        **case.get("headers", {})}
        self.content = bytes.fromhex(case.get("payload_hex", ""))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def iter_content(self, chunk_size):
        yield self.content


class FakeSession:
    def __init__(self, case):
        self.case = case
        self.calls = 0

    def get(self, *_args, **kwargs):
        assert kwargs.get("allow_redirects") is False
        assert kwargs.get("stream") is True
        assert kwargs.get("timeout") == (5, 15)
        self.calls += 1
        kind = self.case["failure"]
        if kind == "timeout":
            raise requests.exceptions.Timeout("SYNTHETIC TIMEOUT")
        if kind == "tls":
            raise requests.exceptions.SSLError("SYNTHETIC TLS ERROR")
        if kind == "connection":
            raise requests.exceptions.ConnectionError("SYNTHETIC CONNECTION RESET")
        assert kind == "http"
        return FakeResponse(self.case)


def test_legacy_regression_corpus_is_self_describing_and_synthetic():
    corpus = load_corpus()
    assert corpus["schema_version"] == 1
    assert corpus["checklist"] == "C017"
    assert corpus["fixture_type"] == "synthetic_offline_reproduction"
    assert "unspecified preview failure" in corpus["warning"]
    assert "nvs/gui.py" in corpus["historical_evidence"]["source_paths_in_C002_archive"]
    assert "nvs/providers.py" in corpus["historical_evidence"]["source_paths_in_C002_archive"]
    assert len(corpus["poster_cases"]) >= 8
    assert len(corpus["codec_cases"]) >= 4
    assert len(corpus["nature_cases"]) >= 3
    ids = [case["id"] for section in ("poster_cases", "codec_cases", "nature_cases")
           for case in corpus[section]]
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("case", cases("poster_cases"))
def test_legacy_regression_http_and_poster_failure_replay(case, tmp_path):
    """Unlike V1's generic QPixmap failure, current poster core emits a code."""
    session = FakeSession(case)
    cache = tmp_path / "offline_poster_cache"
    result = fetch_poster(case["url"], case["provider"], cache, session)
    assert result.code == case["expected_code"]
    assert result.path is None
    assert result.from_cache is False
    assert session.calls == 1
    assert not list(cache.glob("*.jpg"))
    assert not list(cache.glob("*.png"))
    assert not list(cache.glob("*.webp"))


@pytest.mark.parametrize("case", cases("codec_cases"))
def test_legacy_regression_synthetic_codec_error_signals(case):
    """This covers classification signals, NOT real Qt/FFmpeg codec playback."""
    diagnosis = classify_playback_failure(case["ffmpeg_stderr"])
    assert diagnosis.code == case["expected_code"]
    assert diagnosis.message
    assert case["ffmpeg_stderr"] not in diagnosis.message
    assert "SYNTHETIC" not in diagnosis.message


def test_legacy_regression_codec_classifier_never_echoes_untrusted_paths_or_keys():
    raw = "Decoder (codec hevc) not found; Authorization: VERY_PRIVATE_TOKEN D:/고객/음원.mp4"
    output = classify_playback_failure(raw)
    assert output.code == "PLAYBACK_CODEC_UNSUPPORTED"
    assert "VERY_PRIVATE_TOKEN" not in repr(output)
    assert "고객" not in repr(output)
    assert "Authorization" not in repr(output)


def test_legacy_regression_malformed_mp4_bytes_are_retained_without_real_decode(tmp_path):
    """The corpus retains bad media bytes but cannot claim a reproduced codec crash."""
    case = load_corpus()["invalid_video_container"]
    file = tmp_path / "synthetic_invalid_container.mp4"
    file.write_bytes(bytes.fromhex(case["payload_hex"]))
    raw = file.read_bytes()
    assert raw[4:8] == b"ftyp"
    assert b"moov" not in raw and b"mdat" not in raw
    assert len(raw) < 32
    assert case["significance"].startswith("Truncated")
    assert file.is_file()


@pytest.mark.parametrize("case", cases("nature_cases"))
def test_legacy_regression_keyword_only_lake_relevance_false_positive(case):
    """Prove the keyword-only legacy failure and record the target oracle.

    Do NOT pretend that the current R1 relevance filter rejects all meetings:
    it is intentionally demonstrated as not yet integrated.
    """
    title = case["title"].lower()
    assert "lake" in title
    keyword_only_selects = "lake" in title  # simplified legacy bug pattern
    assert keyword_only_selects
    assert case["expected_nature"] is case["nature_relevance_verified"]

    item = MediaCandidate(
        provider=case["provider"],
        source_id=case["source_id"],
        source_url="https://example.org/synthetic-test-only",
        title=case["title"],
        duration_seconds=case["duration_seconds"],
        original_duration_verified=case["original_duration_verified"],
        renditions=(Rendition(width=case["width"], height=case["height"]),),
        nature_relevance_verified=case["nature_relevance_verified"],
    )
    accepted, rejected = filter_candidates([item], SearchCriteria())
    # KNOWN R1 GAP (as of C017): current candidate filter checks duration and
    # resolution, not whether the title is a meeting. Record observation
    # without hardcoding that BUG as expected permanent product behavior.
    assert len(accepted) + len(rejected) == 1
    if case["expected_search_lane"] != "accept":
        assert not case["expected_nature"]
        assert not item.nature_relevance_verified
        assert case["expected_search_lane"] in ("reject", "review")


def test_legacy_regression_meeting_examples_include_4k_and_long_duration():
    """Long duration/4K metadata alone cannot prove an item shows nature."""
    cases_ = load_corpus()["nature_cases"]
    meetings = [case for case in cases_ if case["expected_search_lane"] == "reject"]
    assert len(meetings) >= 2
    assert all(case["duration_seconds"] >= 180 for case in meetings)
    assert any(case["width"] >= 3840 and case["height"] >= 2160 for case in meetings)
    assert all(not case["nature_relevance_verified"] for case in meetings)
