"""C026: Windows Qt GUI selected minimum and optional maximum to real query/filter.

All candidates are synthetic. The shipped trial GUI still has no provider API.
"""
from __future__ import annotations

import os
import time

import pytest

from nature_video_studio.models import MediaCandidate, Rendition, SearchMode
from nature_video_studio.search_coordinator import SearchCoordinator
from nature_video_studio.search_mode_state import LONG_DURATION_PRESETS_SECONDS
from nature_video_studio.source_adapter import SearchPage


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C026 Qt duration widget tests run only on dedicated Windows Qt runner",
)
def test_duration_preset_gui_preset_and_max_independent_with_unavailable_provider():
    Qt = pytest.importorskip("PySide6.QtWidgets")
    app = Qt.QApplication.instance() or Qt.QApplication(["C026"])
    from nature_video_studio.trial_gui import build_window
    window = build_window()
    window.show()
    app.processEvents()

    choices = window.findChild(Qt.QComboBox, "longMinDurationPreset")
    check = window.findChild(Qt.QCheckBox, "longMaxDurationEnabled")
    maximum = window.findChild(Qt.QSpinBox, "longMaxDurationMinutes")
    summary = window.findChild(Qt.QLabel, "longDurationSummary")
    tabs = window.findChild(Qt.QTabWidget, "searchModeTabs")
    button = window.findChild(Qt.QPushButton, "longSearchButton")
    long_input = window.findChild(Qt.QLineEdit, "longSearchQuery")
    short_input = window.findChild(Qt.QLineEdit, "shortSearchQuery")

    assert all(x is not None for x in (
        choices, check, maximum, summary, tabs, button, long_input, short_input,
    ))
    assert [choices.itemData(i) for i in range(choices.count())] == list(
        LONG_DURATION_PRESETS_SECONDS)
    assert choices.currentData() == 180
    assert not check.isChecked()
    assert not maximum.isEnabled()
    assert maximum.value() == 60
    assert "3분 이상 / 최대 제한 없음" in summary.text()

    long_input.setText("겨울 호수")
    short_input.setText("짧은 해변")
    for index, seconds in enumerate(LONG_DURATION_PRESETS_SECONDS):
        choices.setCurrentIndex(index)
        assert choices.currentData() == seconds
        assert f"{seconds // 60}분 이상" in summary.text()
        button.click()
        widget = window.findChild(Qt.QWidget, "trialSearchModes")
        state = widget.session.lane(SearchMode.LONG_ORIGINAL)
        assert state.min_original_duration_seconds == seconds
        assert state.max_original_duration_seconds is None
        assert state.result_count is None

    choices.setCurrentIndex(1)  # 600 seconds
    check.setChecked(True)
    assert maximum.isEnabled()
    maximum.setValue(20)
    assert "10~20분" in summary.text()
    button.click()
    state = widget.session.lane(SearchMode.LONG_ORIGINAL)
    assert state.min_original_duration_seconds == 600
    assert state.max_original_duration_seconds == 1200
    assert "연결되지 않았습니다" in window.findChild(
        Qt.QLabel, "longSearchStatus").text()

    tabs.setCurrentIndex(1)
    assert choices.currentData() == 600
    assert maximum.value() == 20
    assert window.findChild(Qt.QLabel, "shortResultCount").text().endswith("미검색")
    tabs.setCurrentIndex(0)

    seq = state.sequence
    choices.setCurrentIndex(3)  # 1800 seconds but max still 1200.
    assert "조건 오류" in summary.text()
    button.click()
    assert state.sequence == seq
    assert state.min_original_duration_seconds == 600
    assert state.max_original_duration_seconds == 1200
    assert "길이 조건 오류" in window.findChild(
        Qt.QLabel, "longSearchStatus").text()

    check.setChecked(False)
    assert not maximum.isEnabled()
    assert maximum.value() == 20  # stored independently when disabled
    button.click()
    assert state.min_original_duration_seconds == 1800
    assert state.max_original_duration_seconds is None
    assert window.findChild(Qt.QLabel, "shortResultCount").text().endswith("미검색")
    assert long_input.text() == "겨울 호수"
    assert short_input.text() == "짧은 해변"
    window.close()


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C026 Qt async provider query tests run only on dedicated Windows Qt runner",
)
def test_duration_preset_gui_async_query_and_exact_filter_on_windows():
    Qt = pytest.importorskip("PySide6.QtWidgets")
    app = Qt.QApplication.instance() or Qt.QApplication(["C026"])
    from nature_video_studio.search_tabs import SearchTabsWidget

    class RecordingSource:
        name = "Internet Archive"
        supported_modes = frozenset({SearchMode.LONG_ORIGINAL})

        def __init__(self):
            self.queries = []

        async def search(self, query):
            self.queries.append(query)
            return SearchPage(self.name, tuple(MediaCandidate(
                provider=self.name, source_id=str(t), source_url="",
                title=f"synthetic {t} seconds", duration_seconds=t,
                original_duration_verified=True,
                nature_relevance_verified=True, renditions=(Rendition(3840, 2160),),
            ) for t in (179, 180, 599, 600, 1199, 1200, 1201, 1800, 1801)))

    adapter = RecordingSource()
    view = SearchTabsWidget(SearchCoordinator([adapter]))
    view.show()
    app.processEvents()
    pane = view.panes[SearchMode.LONG_ORIGINAL]
    pane.query.setText("lake")
    pane.min_duration.setCurrentIndex(1)
    pane.max_duration_enabled.setChecked(True)
    pane.max_duration_minutes.setValue(20)
    pane.search_button.click()

    until = time.monotonic() + 6
    while time.monotonic() < until:
        app.processEvents()
        if view.session.lane(SearchMode.LONG_ORIGINAL).result_count == 3:
            break
        time.sleep(0.012)

    assert len(adapter.queries) == 1
    criteria = adapter.queries[0].criteria
    assert criteria.min_original_duration_seconds == 600
    assert criteria.max_original_duration_seconds == 1200
    assert view.session.lane(SearchMode.LONG_ORIGINAL).result_count == 3
    assert {x.source_id for x in view.session.lane(
        SearchMode.LONG_ORIGINAL).results} == {"600", "1199", "1200"}
    assert pane.results.rowCount() == 3

    until = time.monotonic() + 4
    while view._threads and time.monotonic() < until:
        app.processEvents()
        time.sleep(0.015)
    assert not view._threads
    view.close()
