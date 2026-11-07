"""C011 trial shell plus C024 independent search-mode tabs.

No provider adapters or user data sources are enabled yet. This remains a
V2 development GUI, not a real footage search/download/playback product.
"""
from __future__ import annotations

import sys

from .version_identity import V2_IDENTITY, validate_trial_identity


def build_window():
    """Import optional Qt only when GUI was explicitly launched."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
    )

    from .search_tabs import SearchTabsWidget

    validate_trial_identity()
    window = QMainWindow()
    window.setObjectName("NVS_V2_TRIAL_WINDOW")
    window.setWindowTitle(V2_IDENTITY.window_title)
    window.resize(900, 660)
    widget = QWidget()
    content = QVBoxLayout(widget)
    content.setContentsMargins(30, 30, 30, 24)
    content.setSpacing(14)

    heading = QLabel(V2_IDENTITY.heading)
    heading.setObjectName("versionHeading")
    heading.setStyleSheet("font-size: 23px; font-weight: 700;")
    content.addWidget(heading)

    notice = QLabel(V2_IDENTITY.caution)
    notice.setObjectName("trialNotice")
    notice.setWordWrap(True)
    notice.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    notice.setStyleSheet("font-size: 14px; line-height: 1.5;")
    content.addWidget(notice)

    state = QLabel("버전 식별 점검: V2 시험판 GUI 실행 중 · V1.0.2와 별도")
    state.setObjectName("versionStatus")
    content.addWidget(state)

    # C024: both independent lanes are visible; without genuine authorized
    # source adapters search clicks correctly return UNAVAILABLE, not fake 0.
    tabs = SearchTabsWidget()
    tabs.setObjectName("trialSearchModes")
    content.addWidget(tabs, 1)

    close = QPushButton("창 닫기")
    close.setObjectName("closeButton")
    close.clicked.connect(window.close)
    content.addWidget(close)
    window.setCentralWidget(widget)
    return window


def main(argv: list[str] | None = None) -> int:
    """--smoke tests only title and content; no OS GUI screenshot is claimed."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["--smoke"]):
        print("사용법: python -m nature_video_studio [--smoke]")
        return 2
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("C011_GUI_DEPENDENCY_MISSING: PySide6 (별도 설치 필요)")
        return 2

    app = QApplication.instance() or QApplication(["Nature Video Studio V2 trial"])
    window = build_window()
    if argv == ["--smoke"]:
        if "[V2 시험판]" not in window.windowTitle():
            print("C011_GUI_SMOKE_FAIL")
            return 1
        print("C011_GUI_SMOKE_PASS")
        print("TITLE_UNICODE_ESCAPE: " + window.windowTitle().encode("unicode_escape").decode("ascii"))
        print("WINDOW_OBJECT_NAME: " + window.objectName())
        print("V1_DATA_READ_OR_WRITTEN: False")
        print("REAL_WINDOWS_TITLEBAR_CAPTURE: SKIP_NOT_RUN")
        window.close()
        return 0

    window.show()
    return app.exec()
