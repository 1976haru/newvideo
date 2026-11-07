"""C024 Qt widget tests, gated to dedicated Windows Qt CI job.

Headless CI on Linux/Windows only runs search-mode model/contract tests.
Actual native GUI screenshot remains the separate C022 job.
"""
import os
import time

import pytest


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C024 GUI assertions run in dedicated Windows Qt job",
)
def test_search_mode_isolation_gui_independent_tabs_sort_counts_and_switch():
    qt = pytest.importorskip("PySide6.QtWidgets")
    app = qt.QApplication.instance() or qt.QApplication(["C024"])
    from nature_video_studio.trial_gui import build_window
    from nature_video_studio.models import SearchMode
    from nature_video_studio.search_mode_state import LaneStatus

    window = build_window()
    window.show()
    app.processEvents()
    tabs = window.findChild(qt.QTabWidget, "searchModeTabs")
    assert tabs is not None
    assert tabs.count() == 2
    assert tabs.tabText(0) == "3분 이상 원본"
    assert tabs.tabText(1) == "짧은 영상 조합"
    assert tabs.currentIndex() == 0

    long_text = window.findChild(qt.QLineEdit, "longSearchQuery")
    short_text = window.findChild(qt.QLineEdit, "shortSearchQuery")
    assert long_text is not None and short_text is not None
    long_text.setText("겨울 호수 30분")
    short_text.setText("짧은 해변 영상")

    long_sort = window.findChild(qt.QComboBox, "longSortChoice")
    short_sort = window.findChild(qt.QComboBox, "shortSortChoice")
    assert long_sort.currentText() == "원본 길이 긴 순"
    assert short_sort.currentText() == "짧은 컷부터"
    long_sort.setCurrentIndex(1)
    assert long_sort.currentText() == "4K·풍경 적합도 우선"
    assert short_sort.currentText() == "짧은 컷부터"

    long_switch = window.findChild(qt.QPushButton, "longSwitchMode")
    short_switch = window.findChild(qt.QPushButton, "shortSwitchMode")
    long_switch.click()
    assert tabs.currentIndex() == 1
    assert short_switch.isVisible()
    assert long_text.text() == "겨울 호수 30분"

    # With no real official source adapter, clicks report UNAVAILABLE rather
    # than a fabricated 0 hit count or populated mock search results.
    window.findChild(qt.QPushButton, "shortSearchButton").click()
    assert window.findChild(qt.QLabel, "shortResultCount").text().endswith("확인 불가")
    assert "연결되지 않았습니다" in window.findChild(
        qt.QLabel, "shortSearchStatus").text()
    assert window.findChild(qt.QLabel, "longResultCount").text().endswith("미검색")

    short_switch.click()
    assert tabs.currentIndex() == 0
    window.findChild(qt.QPushButton, "longSearchButton").click()
    assert window.findChild(qt.QLabel, "longResultCount").text().endswith("확인 불가")
    assert window.findChild(qt.QLabel, "shortResultCount").text().endswith("확인 불가")

    widget = window.findChild(qt.QWidget, "trialSearchModes")
    assert widget.session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.UNAVAILABLE
    assert widget.session.lane(SearchMode.SHORT_COMPOSER).status == LaneStatus.UNAVAILABLE
    assert long_text.text() == "겨울 호수 30분"
    assert short_text.text() == "짧은 해변 영상"
    window.close()


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C024 async search Qt worker runs in dedicated Windows Qt job",
)
def test_search_mode_isolation_gui_async_worker_uses_only_target_lane():
    qt = pytest.importorskip("PySide6.QtWidgets")
    app = qt.QApplication.instance() or qt.QApplication(["C024"])
    from nature_video_studio.models import SearchMode
    from nature_video_studio.search_coordinator import SearchCoordinator
    from nature_video_studio.search_tabs import SearchTabsWidget
    from nature_video_studio.source_adapter import SearchPage
    from nature_video_studio.models import MediaCandidate, Rendition

    class Adapter:
        def __init__(self, name, mode, duration):
            self.name, self.supported_modes, self.duration = name, frozenset({mode}), duration
            self.called_modes = []

        async def search(self, query):
            self.called_modes.append(query.criteria.mode)
            return SearchPage(self.name, (
                MediaCandidate(
                    provider=self.name, source_id="mock", title="합성 호수",
                    source_url="https://example.org/fixture-only",
                    duration_seconds=self.duration, original_duration_verified=True,
                    renditions=(Rendition(3840, 2160),), nature_relevance_verified=True,
                ),
            ))

    long = Adapter("Internet Archive", SearchMode.LONG_ORIGINAL, 400)
    short = Adapter("Pexels", SearchMode.SHORT_COMPOSER, 20)
    window = SearchTabsWidget(SearchCoordinator([long, short]))
    window.show()
    app.processEvents()
    window.panes[SearchMode.LONG_ORIGINAL].query.setText("산")
    window.panes[SearchMode.SHORT_COMPOSER].query.setText("해변")
    window.panes[SearchMode.LONG_ORIGINAL].search_button.click()
    window.panes[SearchMode.SHORT_COMPOSER].search_button.click()

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.processEvents()
        if (
            window.session.lane(SearchMode.LONG_ORIGINAL).result_count == 1
            and window.session.lane(SearchMode.SHORT_COMPOSER).result_count == 1
        ):
            break
        time.sleep(0.015)
    assert window.session.lane(SearchMode.LONG_ORIGINAL).result_count == 1
    assert window.session.lane(SearchMode.SHORT_COMPOSER).result_count == 1
    assert long.called_modes == [SearchMode.LONG_ORIGINAL]
    assert short.called_modes == [SearchMode.SHORT_COMPOSER]
    assert window.panes[SearchMode.LONG_ORIGINAL].results.rowCount() == 1
    assert window.panes[SearchMode.SHORT_COMPOSER].results.rowCount() == 1

    deadline = time.monotonic() + 2
    while window._threads and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert not window._threads
    window.close()
