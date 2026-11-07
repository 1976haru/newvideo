"""C028 visible Pexels 120-second policy on both Qt search lanes."""
from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C028 Qt policy UI runs on separate Windows Qt runner",
)
def test_pexels_lane_gui_labels_and_manual_tabs_without_fabricated_search():
    Qt = pytest.importorskip("PySide6.QtWidgets")
    app = Qt.QApplication.instance() or Qt.QApplication(["C028"])
    from nature_video_studio.trial_gui import build_window
    from nature_video_studio.models import SearchMode
    from nature_video_studio.search_mode_state import LaneStatus

    window = build_window(live_providers=False)
    window.show()
    app.processEvents()
    tabs = window.findChild(Qt.QTabWidget, "searchModeTabs")
    long_policy = window.findChild(Qt.QLabel, "longProviderPolicy")
    short_policy = window.findChild(Qt.QLabel, "shortProviderPolicy")
    assert long_policy is not None and short_policy is not None
    assert long_policy.isVisible()
    assert "Pexels" in long_policy.text()
    assert "최대 120초" in long_policy.text()
    assert "장편 원본 공급처에서 제외" in long_policy.text()
    assert "실제 제공처 미연결" in long_policy.text()
    assert "5~120초" in short_policy.text()
    assert "클립 전용" in short_policy.text()
    assert "상업적 재사용" in short_policy.text()
    assert tabs.currentIndex() == 0
    assert not short_policy.isVisible()
    long_search = window.findChild(Qt.QLineEdit, "longSearchQuery")
    long_search.setText("호수")
    window.findChild(Qt.QPushButton, "longSearchButton").click()
    assert "확인 불가" in window.findChild(Qt.QLabel, "longResultCount").text()
    widget = window.findChild(Qt.QWidget, "trialSearchModes")
    assert widget.session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.UNAVAILABLE
    assert tabs.currentIndex() == 0
    assert widget.session.lane(SearchMode.SHORT_COMPOSER).status == LaneStatus.NOT_SEARCHED
    window.findChild(Qt.QPushButton, "longSwitchMode").click()
    app.processEvents()
    assert tabs.currentIndex() == 1
    assert short_policy.isVisible()
    assert "미검색" in window.findChild(Qt.QLabel, "shortResultCount").text()
    short_search = window.findChild(Qt.QLineEdit, "shortSearchQuery")
    short_search.setText("짧은 호수")
    window.findChild(Qt.QPushButton, "shortSearchButton").click()
    assert "확인 불가" in window.findChild(Qt.QLabel, "shortResultCount").text()
    assert widget.session.lane(SearchMode.SHORT_COMPOSER).status == LaneStatus.UNAVAILABLE
    assert widget.session.lane(SearchMode.LONG_ORIGINAL).status == LaneStatus.UNAVAILABLE
    window.close()
