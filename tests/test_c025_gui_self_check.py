"""C025 real Qt widget self-check buttons: separate from live provider search."""
from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="C025 GUI self-test runs only in dedicated Windows Qt job",
)
def test_c025_gui_180_self_test_button_shows_offline_report(monkeypatch):
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["C025"])
    from nature_video_studio.trial_gui import build_window

    window = build_window()
    window.show()
    app.processEvents()
    button = window.findChild(QtWidgets.QPushButton, "longDurationSelfCheck")
    assert button is not None and button.isVisible()

    captured = {}
    def show(_parent, title, message):
        captured.update(title=title, message=message)
        return QtWidgets.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", show)
    button.click()
    assert "C025" in captured["title"]
    assert "테스트용 합성 데이터" in captured["message"]
    assert "179초 단일 원본 → 장편 제외" in captured["message"]
    assert "180초 단일 원본 → 장편 포함" in captured["message"]
    assert "60초 × 3개 = 180초 조합 → 장편 제외" in captured["message"]
    assert "판정: 8/8 PASS" in captured["message"]
    # Running the self-check does not fabricate real search results.
    count = window.findChild(QtWidgets.QLabel, "longResultCount")
    assert count.text().endswith("미검색")
    window.close()
