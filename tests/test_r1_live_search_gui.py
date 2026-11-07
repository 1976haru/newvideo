"""R1 LIVE adapter integration: actual GUI wiring, synthetic API network fixtures.

These tests DO NOT claim live internet access, a working media player, or rights.
"""
from __future__ import annotations

import asyncio
import os
import time

import pytest

from nature_video_studio.commons_adapter import CommonsLongAdapter
from nature_video_studio.live_sources import make_live_sources
from nature_video_studio.models import SearchMode, ResolutionMode
from nature_video_studio.pixabay_official_adapter import (
    PixabayVideoAdapter, PixabayServiceError, KEYRING_SERVICE,
)
from nature_video_studio.search_coordinator import SearchCoordinator
from nature_video_studio.search_mode_state import LaneStatus
from nature_video_studio.source_adapter import SearchQuery
from nature_video_studio.filtering import SearchCriteria


def pixabay_hit(duration: int, video_id: int):
    return {
        "id": video_id,
        "pageURL": f"https://pixabay.com/videos/lake-nature-{video_id}/",
        "tags": "lake nature",
        "duration": duration, "user": "Landscape Artist",
        "videos": {
            "large": {
                "url": f"https://cdn.pixabay.com/video/2023/01/01/lake-{video_id}.mp4",
                "width": 3840, "height": 2160, "size": 150_000_000,
                "thumbnail": "",
            },
            "medium": {
                "url": f"https://cdn.pixabay.com/video/2023/01/01/lake-{video_id}-med.mp4",
                "width": 1920, "height": 1080, "size": 40_000_000,
            },
        }
    }


def fake_pixabay_api(params):
    assert params["video_type"] == "film"
    assert params["q"] == "lake"
    assert params["per_page"] == 20
    assert params["lang"] == "ko"
    assert params["key"] == "TEST_KEY_NOT_REAL_123456789"
    return {"totalHits": 2, "hits": [pixabay_hit(200, 123), pixabay_hit(20, 456)]}


def test_live_sources_factory_constructs_two_real_adapters_without_network(monkeypatch):
    import nature_video_studio.live_sources as live
    def blocked(*args, **kwargs):
        raise AssertionError("No network or key access during app construction")
    monkeypatch.setattr("nature_video_studio.commons_adapter._fetch_official", blocked)
    monkeypatch.setattr("nature_video_studio.pixabay_official_adapter._fetch_official", blocked)
    sources = live.make_live_sources()
    assert sources.pixabay.name == "Pixabay"
    assert [a.name for a in sources.coordinator._adapters] == [
        "Wikimedia Commons", "Pixabay"
    ]


def test_live_pixabay_official_api_key_only_used_during_request():
    called = []
    def key():
        called.append(True)
        return "TEST_KEY_NOT_REAL_123456789"
    pages = []
    def api(p):
        pages.append(dict(p))
        return fake_pixabay_api(p)
    source = PixabayVideoAdapter(api, key)
    coordinator = SearchCoordinator([
        CommonsLongAdapter(lambda p: {"query": {"pages": []}}), source
    ])
    assert called == [] and pages == []
    long = asyncio.run(coordinator.search(SearchQuery("lake")))
    assert [c.source_id for c in long.accepted] == ["123"]
    assert [p.code for p in long.providers] == ["OK", "OK"]
    short = asyncio.run(coordinator.search(SearchQuery(
        "lake", SearchCriteria(mode=SearchMode.SHORT_COMPOSER)
    )))
    assert [c.source_id for c in short.accepted] == ["456"]
    assert [p.code for p in short.providers] == ["MODE_UNSUPPORTED", "OK"]
    # Same user query cached after first request for 24h inside session.
    assert len(pages) == 1


def test_live_pixabay_missing_key_is_status_not_zero_or_raw_exception():
    source = PixabayVideoAdapter(lambda _: pytest.fail("should not request"), lambda: None)
    outcome = asyncio.run(SearchCoordinator([source]).search(SearchQuery(
        "lake", SearchCriteria(mode=SearchMode.SHORT_COMPOSER)
    )))
    assert not outcome.accepted
    assert outcome.providers[0].code == "API_KEY_MISSING"
    assert "TEST_KEY" not in repr(outcome)


def test_live_pixabay_session_key_does_not_require_writing_legacy_key():
    def forbidden():
        raise AssertionError("Do not read or write original V1 key after manual session key")
    source = PixabayVideoAdapter(fake_pixabay_api, forbidden)
    assert source.set_session_key("TEST_KEY_NOT_REAL_123456789")
    page = asyncio.run(source.search(SearchQuery("lake")))
    assert len(page.candidates) == 2
    assert KEYRING_SERVICE == "NatureVideoStudio_2026"


def test_live_pixabay_rate_limit_without_requests_burst():
    calls = []
    source = PixabayVideoAdapter(
        lambda p: calls.append(1) or fake_pixabay_api(p),
        lambda: "TEST_KEY_NOT_REAL_123456789"
    )
    asyncio.run(source.search(SearchQuery("lake")))
    with pytest.raises(PixabayServiceError, match="PIXABAY_RATE_LIMIT"):
        asyncio.run(source.search(SearchQuery("mountain")))
    assert calls == [1]


@pytest.mark.skipif(not os.environ.get("NVS_RUN_QT_TESTS"),
                    reason="Real Qt live provider UI fixture runs on Windows Qt CI")
def test_live_qt_window_wires_two_real_services_and_does_not_fetch_on_startup(monkeypatch):
    qt = pytest.importorskip("PySide6.QtWidgets")
    app = qt.QApplication.instance() or qt.QApplication(["R1-LIVE"])
    from nature_video_studio.trial_gui import build_window
    from nature_video_studio.live_gui import LiveSearchTabsWidget
    win = build_window()
    tabs = win.findChild(LiveSearchTabsWidget, "trialSearchModes")
    assert tabs is not None
    assert tabs.coordinator is not None
    assert "Wikimedia Commons" in [a.name for a in tabs.coordinator._adapters]
    assert "Pixabay" in [a.name for a in tabs.coordinator._adapters]
    assert win.findChild(qt.QLineEdit, "pixabaySessionKey") is not None
    assert win.findChild(qt.QPushButton, "longSearchButton") is not None
    assert win.findChild(qt.QPushButton, "shortSearchButton") is not None
    assert win.findChild(qt.QLabel, "realProviderNotice") is not None
    assert "실제 API" in win.findChild(qt.QLabel, "realProviderNotice").text()
    assert tabs.session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.NOT_SEARCHED
    assert tabs.session.lane(SearchMode.SHORT_COMPOSER).status == LaneStatus.NOT_SEARCHED
    win.close()


@pytest.mark.skipif(not os.environ.get("NVS_RUN_QT_TESTS"),
                    reason="Actual Qt interaction uses mocked provider HTTP responses")
def test_live_qt_real_search_ui_shows_results_detail_rights_and_manual_source(monkeypatch):
    qt = pytest.importorskip("PySide6.QtWidgets")
    app = qt.QApplication.instance() or qt.QApplication(["R1-LIVE"])
    from nature_video_studio.live_gui import LiveSearchTabsWidget, safe_source_page
    pixabay = PixabayVideoAdapter(fake_pixabay_api, lambda: "TEST_KEY_NOT_REAL_123456789")
    coordinator = SearchCoordinator([
        CommonsLongAdapter(lambda p: {"query": {"pages": []}}), pixabay
    ])
    widget = LiveSearchTabsWidget(coordinator, pixabay)
    widget.show()
    app.processEvents()
    long = widget.panes[SearchMode.LONG_ORIGINAL]
    short = widget.panes[SearchMode.SHORT_COMPOSER]
    long.query.setText("lake")
    long.search_button.click()
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        app.processEvents()
        if widget.session.lane(SearchMode.LONG_ORIGINAL).result_count == 1:
            break
        time.sleep(.01)
    assert long.results.rowCount() == 1
    assert long.results.item(0, 1).text() == "03:20"
    assert widget.session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.RESULTS
    long.results.selectRow(0)
    app.processEvents()
    assert "Landscape Artist" in long.detail.text()
    assert "general_review" in long.detail.text()
    assert long.source_link.isEnabled()
    assert "Pixabay" in long.provider_details.text()
    assert "정상 응답" in long.provider_details.text()
    assert safe_source_page(widget.session.lane(SearchMode.LONG_ORIGINAL).results[0])
    assert widget.session.lane(SearchMode.SHORT_COMPOSER).result_count is None
    short.query.setText("lake")
    short.search_button.click()
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        app.processEvents()
        if widget.session.lane(SearchMode.SHORT_COMPOSER).result_count == 1:
            break
        time.sleep(.01)
    assert short.results.rowCount() == 1
    assert short.results.item(0, 1).text() == "00:20"
    assert widget.session.lane(SearchMode.LONG_ORIGINAL).result_count == 1
    while (widget._threads or widget._poster_workers) and time.monotonic() < deadline+2:
        app.processEvents()
        time.sleep(.01)
    widget.close()
