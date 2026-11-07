"""C011 Qt smoke is optional locally; Windows Qt CI job tests real widgets.

A QPA offscreen smoke does not count as a real Windows titlebar screenshot.
"""
import os
import pytest

from nature_video_studio.version_identity import V2_IDENTITY


@pytest.mark.skipif(
    not os.environ.get("NVS_RUN_QT_TESTS"),
    reason="Qt smoke in dedicated Windows GUI CI job only",
)
def test_qt_trial_window_title_and_visible_labels():
    qt = pytest.importorskip("PySide6.QtWidgets")
    app = qt.QApplication.instance() or qt.QApplication(["NVS-C011-test"])
    from nature_video_studio.trial_gui import build_window

    window = build_window()
    assert window.windowTitle() == V2_IDENTITY.window_title
    assert window.objectName() == "NVS_V2_TRIAL_WINDOW"
    assert window.findChild(qt.QLabel, "versionHeading").text() == V2_IDENTITY.heading
    assert "기존 V1.0.2" in window.findChild(qt.QLabel, "trialNotice").text()
    assert window.findChild(qt.QPushButton, "closeButton") is not None
    assert "V2 시험판" in window.findChild(qt.QLabel, "versionStatus").text()
    window.close()
