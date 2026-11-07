"""C027 GUI - exact 0 vs unavailable, explicit alternative click only.

Includes an explicitly marked offline 0-result demonstration because the
user's current trial build deliberately has no live provider adapters.
"""
from __future__ import annotations

import os
import time

import pytest


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C027 Qt buttons run only on dedicated Windows Qt runner",
)
def test_no_silent_fallback_gui_offline_demo_requires_user_to_switch():
    Qt = pytest.importorskip("PySide6.QtWidgets")
    from nature_video_studio.trial_gui import build_window
    from nature_video_studio.models import SearchMode
    from nature_video_studio.search_mode_state import LaneStatus

    app = Qt.QApplication.instance() or Qt.QApplication(["C027"])
    window = build_window()
    window.show()
    app.processEvents()
    tabs = window.findChild(Qt.QTabWidget, "searchModeTabs")
    demo = window.findChild(Qt.QPushButton, "longOfflineZeroDemo")
    alternative = window.findChild(Qt.QPushButton, "longNoResultsAlternative")
    long_count = window.findChild(Qt.QLabel, "longResultCount")
    short_count = window.findChild(Qt.QLabel, "shortResultCount")
    status = window.findChild(Qt.QLabel, "longSearchStatus")
    assert tabs.currentIndex() == 0
    assert demo is not None and demo.isVisible()
    assert alternative is not None and not alternative.isVisible()
    assert long_count.text().endswith("미검색")
    assert short_count.text().endswith("미검색")

    demo.click()
    app.processEvents()
    widget = window.findChild(Qt.QWidget, "trialSearchModes")
    lane = widget.session.lane(SearchMode.LONG_ORIGINAL)
    assert lane.status == LaneStatus.EMPTY
    assert lane.offline_zero_demo
    assert lane.result_count == 0
    assert tabs.currentIndex() == 0  # never silently switch
    assert "0건 (오프라인 테스트)" in long_count.text()
    assert "실제 제공처 검색 아님" in status.text()
    assert "자동 혼합·전환·검색·다운로드 없음" in status.text()
    assert alternative.isVisible()
    assert short_count.text().endswith("미검색")

    alternative.click()
    app.processEvents()
    assert tabs.currentIndex() == 1
    assert short_count.text().endswith("미검색")
    assert widget.session.lane(SearchMode.SHORT_COMPOSER).status == LaneStatus.NOT_SEARCHED
    tabs.setCurrentIndex(0)
    q = window.findChild(Qt.QLineEdit, "longSearchQuery")
    q.setText("호수")
    window.findChild(Qt.QPushButton, "longSearchButton").click()
    app.processEvents()
    assert lane.status == LaneStatus.UNAVAILABLE
    assert not lane.offline_zero_demo
    assert "확인 불가" in long_count.text()
    assert "연결되지 않았습니다" in status.text()
    assert not alternative.isVisible()
    assert short_count.text().endswith("미검색")
    window.close()


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C027 Qt fake provider search runs only on dedicated Windows Qt runner",
)
def test_no_silent_fallback_gui_provider_zero_does_not_search_short_until_click():
    Qt = pytest.importorskip("PySide6.QtWidgets")
    from nature_video_studio.models import MediaCandidate, Rendition, SearchMode
    from nature_video_studio.search_coordinator import SearchCoordinator
    from nature_video_studio.search_tabs import SearchTabsWidget
    from nature_video_studio.source_adapter import SearchPage
    from nature_video_studio.search_mode_state import LaneStatus

    app = Qt.QApplication.instance() or Qt.QApplication(["C027"])
    class FakeSource:
        def __init__(self, name, mode, duration):
            self.name, self.mode, self.duration = name, mode, duration
            self.supported_modes = frozenset({mode})
            self.calls = 0

        async def search(self, query):
            self.calls += 1
            return SearchPage(self.name, (
                MediaCandidate(
                    provider=self.name, source_id="short-or-filtered",
                    source_url="", title="offline synthetic",
                    duration_seconds=self.duration,
                    original_duration_verified=True,
                    renditions=(Rendition(3840, 2160),),
                    nature_relevance_verified=True,
                ),
            ))

    long = FakeSource("Internet Archive", SearchMode.LONG_ORIGINAL, 120)
    short = FakeSource("Pexels", SearchMode.SHORT_COMPOSER, 20)
    window = SearchTabsWidget(SearchCoordinator([long, short]))
    window.show()
    app.processEvents()
    pane = window.panes[SearchMode.LONG_ORIGINAL]
    pane.query.setText("호수")
    pane.search_button.click()
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        app.processEvents()
        if window.session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.EMPTY:
            break
        time.sleep(0.012)

    assert window.session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.EMPTY
    assert pane.count.text().endswith("0건")
    assert pane.alternative_button.isVisible()
    assert window.tabs.currentIndex() == 0
    assert window.session.active_mode == SearchMode.LONG_ORIGINAL
    assert long.calls == 1
    assert short.calls == 0
    pane.alternative_button.click()
    app.processEvents()
    assert window.tabs.currentIndex() == 1
    assert short.calls == 0
    assert window.session.lane(SearchMode.SHORT_COMPOSER).result_count is None
    shorts = window.panes[SearchMode.SHORT_COMPOSER]
    shorts.query.setText("짧은 해변")
    shorts.search_button.click()
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        app.processEvents()
        if window.session.lane(SearchMode.SHORT_COMPOSER).result_count == 1:
            break
        time.sleep(0.012)
    assert short.calls == 1
    assert window.session.lane(SearchMode.SHORT_COMPOSER).result_count == 1
    assert window.session.lane(SearchMode.LONG_ORIGINAL).result_count == 0
    end = time.monotonic() + 4
    while window._threads and time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)
    assert not window._threads
    window.close()


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C027 Qt partial provider state runs only on dedicated Windows Qt runner",
)
def test_no_silent_fallback_gui_partial_zero_never_offers_confirmed_empty_cta():
    Qt = pytest.importorskip("PySide6.QtWidgets")
    from nature_video_studio.models import SearchMode
    from nature_video_studio.search_coordinator import ProviderStatus, SearchOutcome
    from nature_video_studio.search_tabs import SearchTabsWidget
    from nature_video_studio.search_mode_state import LaneStatus

    app = Qt.QApplication.instance() or Qt.QApplication(["C027"])
    widget = SearchTabsWidget()
    widget.show()
    app.processEvents()
    ticket = widget.session.begin_search(SearchMode.LONG_ORIGINAL, "lake")
    widget._complete(ticket, SearchOutcome(
        accepted=(), rejected={},
        providers=(ProviderStatus("Internet Archive", "PROVIDER_FAILED"),
                   ProviderStatus("Wikimedia Commons", "OK", 0)),
    ))
    pane = widget.panes[SearchMode.LONG_ORIGINAL]
    assert widget.session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.PARTIAL
    assert "0건 (부분 결과·전체 미확인)" in pane.count.text()
    assert not pane.alternative_button.isVisible()
    assert "전체 원본이 0건인지는 확인할 수 없습니다" in pane.status_label.text()
    assert widget.tabs.currentIndex() == 0
    widget.close()
