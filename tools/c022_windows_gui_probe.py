"""C022: Windows-native Qt trial GUI capture, NOT an offscreen widget test.

Only creates proof files under an explicitly passed CI temp directory. It does
not access user media, databases, API keys, or network resources.

Exit code 0 requires BOTH a working visible native window and a captured
Windows QScreen image. Captured pixels do NOT by themselves prove title-bar
text legibility; the windowTitle and widget labels are checked separately.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def _colors(pixmap):
    """Cheap nonblankness check; not an OCR or visual titlebar verification."""
    image = pixmap.toImage()
    if image.isNull():
        return 0
    colors = set()
    for i in range(11):
        for j in range(7):
            x = min(image.width() - 1, max(0, i * (image.width() - 1) // 10))
            y = min(image.height() - 1, max(0, j * (image.height() - 1) // 6))
            colors.add(image.pixel(x, y))
    return len(colors)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("C022_USAGE_ERROR: exactly one output directory required")
        return 2
    if sys.platform != "win32":
        print("C022_NATIVE_WINDOWS_SKIP_NOT_RUN")
        return 3
    if os.environ.get("QT_QPA_PLATFORM", "").lower() in ("offscreen", "minimal"):
        print("C022_NATIVE_GUI_FAIL: offscreen/minimal Qt platform is forbidden")
        return 4
    # Native plugin must be requested explicitly; never inherit a headless QPA.
    os.environ["QT_QPA_PLATFORM"] = "windows"
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QLabel, QPushButton, QSpinBox, QTabWidget,
    )
    from nature_video_studio.trial_gui import build_window
    from nature_video_studio.version_identity import V2_IDENTITY

    app = QApplication.instance() or QApplication(["C022 Windows trial QA"])
    if app.platformName().lower() != "windows":
        print("C022_NATIVE_GUI_FAIL: not using Qt Windows platform plugin")
        return 5

    window = build_window()
    window.move(80, 80)
    window.show()
    window.raise_()
    window.activateWindow()
    for _ in range(8):
        app.processEvents()
        time.sleep(0.08)

    if not window.isVisible() or window.windowTitle() != V2_IDENTITY.window_title:
        print("C022_NATIVE_GUI_FAIL: actual visible trial window/title missing")
        return 6
    if not (
        window.findChild(QLabel, "versionHeading")
        and window.findChild(QLabel, "versionHeading").text() == V2_IDENTITY.heading
        and window.findChild(QLabel, "trialNotice")
        and "기존 V1.0.2" in window.findChild(QLabel, "trialNotice").text()
        and window.findChild(QPushButton, "closeButton")
    ):
        print("C022_NATIVE_GUI_FAIL: labels or close button are missing")
        return 7

    # C024 native Windows smoke: verify both newly visible search modes
    # without confusing an unconnected adapter with a successful live search.
    modes = window.findChild(QTabWidget, "searchModeTabs")
    if (
        modes is None or modes.count() != 2
        or modes.tabText(0) != "3분 이상 원본"
        or modes.tabText(1) != "짧은 영상 조합"
        or window.findChild(QPushButton, "longSwitchMode") is None
        or window.findChild(QPushButton, "shortSwitchMode") is None
        or window.findChild(QLabel, "longResultCount") is None
        or window.findChild(QLabel, "shortResultCount") is None
        or window.findChild(QPushButton, "longDurationSelfCheck") is None
    ):
        print("C024_WINDOWS_SEARCH_TABS_FAIL: separate controls missing")
        return 14

    # C026: assert real native Qt window contains all four precise presets
    # and an independently optional maximum bound.
    minimum = window.findChild(QComboBox, "longMinDurationPreset")
    maximum_enabled = window.findChild(QCheckBox, "longMaxDurationEnabled")
    maximum = window.findChild(QSpinBox, "longMaxDurationMinutes")
    if (
        minimum is None or maximum_enabled is None or maximum is None
        or [minimum.itemData(i) for i in range(minimum.count())]
        != [180, 600, 1200, 1800]
        or minimum.currentData() != 180
        or maximum_enabled.isChecked() or maximum.isEnabled()
    ):
        print("C026_WINDOWS_PRESETS_AND_MAX_FAIL")
        return 15

    # C027: real native Qt trial displays a separately labelled offline
    # demo and a hidden alternative until the long lane is confirmed EMPTY.
    from nature_video_studio.models import SearchMode
    from nature_video_studio.search_mode_state import LaneStatus
    demo = window.findChild(QPushButton, "longOfflineZeroDemo")
    alternative = window.findChild(QPushButton, "longNoResultsAlternative")
    if demo is None or alternative is None or alternative.isVisible():
        print("C027_WINDOWS_ZERO_ALTERNATIVE_INITIAL_STATE_FAIL")
        return 16

    handle = int(window.winId())
    if not handle or not ctypes.windll.user32.IsWindow(handle):
        print("C022_NATIVE_GUI_FAIL: Windows HWND missing")
        return 8
    screen = window.screen() or QApplication.primaryScreen()
    if screen is None:
        print("C022_NATIVE_GUI_FAIL: no Windows screen")
        return 9
    window_pixmap = window.grab()
    native_pixmap = screen.grabWindow(handle)
    if (
        native_pixmap.isNull() or window_pixmap.isNull()
        or native_pixmap.width() < 400 or native_pixmap.height() < 160
        or _colors(native_pixmap) < 3
        or _colors(window_pixmap) < 3
    ):
        print("C022_NATIVE_GUI_FAIL: blank or unavailable native window capture")
        return 10

    folder = Path(argv[0]).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    native_png = folder / "c022_native_window_capture.png"
    qt_png = folder / "c022_qt_client_capture.png"
    if not native_pixmap.save(str(native_png), "PNG"):
        print("C022_NATIVE_GUI_FAIL: native screenshot write failed")
        return 11
    if not window_pixmap.save(str(qt_png), "PNG"):
        print("C022_NATIVE_GUI_FAIL: Qt client screenshot write failed")
        return 12

    # User-driven offline sample follows the normal EMPTY rendering but is
    # explicitly marked synthetic; it MUST NOT switch lanes on its own.
    demo.click()
    app.processEvents()
    active_long = window.findChild(QTabWidget, "searchModeTabs")
    count_long = window.findChild(QLabel, "longResultCount")
    status_long = window.findChild(QLabel, "longSearchStatus")
    count_short = window.findChild(QLabel, "shortResultCount")
    if (active_long.currentIndex() != 0 or not alternative.isVisible()
            or "0건" not in count_long.text() or "오프라인 테스트" not in count_long.text()
            or "실제 제공처 검색 아님" not in status_long.text()
            or not count_short.text().endswith("미검색")):
        print("C027_WINDOWS_OFFLINE_ZERO_FAIL")
        return 17
    alternative.click()
    app.processEvents()
    if (active_long.currentIndex() != 1 or not count_short.text().endswith("미검색")):
        print("C027_WINDOWS_EXPLICIT_SWITCH_ONLY_FAIL")
        return 18
    active_long.setCurrentIndex(0)
    from PySide6.QtWidgets import QLineEdit
    window.findChild(QLineEdit, "longSearchQuery").setText("호수")
    window.findChild(QPushButton, "longSearchButton").click()
    app.processEvents()
    if (alternative.isVisible() or "0건" in count_long.text()
            or "연결되지 않았습니다" not in status_long.text()
            or active_long.currentIndex() != 0):
        print("C027_WINDOWS_UNAVAILABLE_IS_NOT_ZERO_FAIL")
        return 19

    snapshot = {
        "checklist": "C022",
        "test_kind": "WINDOWS_NATIVE_QT_TRIAL_GUI_SCREENSHOT",
        "platform": sys.platform,
        "qpa_platform": app.platformName(),
        "window_visible": window.isVisible(),
        "native_hwnd_present": True,
        "window_title": window.windowTitle(),
        "window_object_name": window.objectName(),
        "native_window_png_sha256": hashlib.sha256(native_png.read_bytes()).hexdigest(),
        "qt_client_png_sha256": hashlib.sha256(qt_png.read_bytes()).hexdigest(),
        "native_dimensions": [native_pixmap.width(), native_pixmap.height()],
        "qt_client_dimensions": [window_pixmap.width(), window_pixmap.height()],
        "native_pixel_colors_sampled": _colors(native_pixmap),
        "visible_native_titlebar_text_ocr": "NOT_TESTED",
        "c024_search_tabs": ["3분 이상 원본", "짧은 영상 조합"],
        "c024_provider_search": "NOT_CONNECTED",
        "c025_duration_self_check_button": "PRESENT",
        "c025_live_source_duration_verification": "NOT_CONNECTED",
        "c026_min_original_presets_seconds": [180, 600, 1200, 1800],
        "c026_separate_optional_max_limit": "PRESENT_OFF_BY_DEFAULT",
        "c026_live_api_filters": "NOT_CONNECTED",
        "c027_offline_zero_demo": "PASS_EXPLICIT_TEST_ONLY",
        "c027_zero_alternative_requires_click": "PASS",
        "c027_no_provider_must_not_show_zero": "PASS",
        "real_search_download_preview_composer": "NOT_IMPLEMENTED",
        "user_v1_data_validation": "NOT_TESTED",
    }
    (folder / "c022_native_gui_evidence.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    close = window.findChild(QPushButton, "closeButton")
    close.click()
    app.processEvents()
    if window.isVisible():
        print("C022_NATIVE_GUI_FAIL: close button did not close window")
        return 13
    print("C027_WINDOWS_NATIVE_NO_SILENT_FALLBACK_PASS")
    print("C027_LIVE_ZERO_RESULT_SEARCH: SKIP_PROVIDER_NOT_CONNECTED")
    print("C026_WINDOWS_NATIVE_DURATION_PRESETS_PASS")
    print("C026_LIVE_PROVIDER_FILTER: SKIP_NOT_CONNECTED")
    print("C024_WINDOWS_NATIVE_SEARCH_TABS_PASS")
    print("C024_LIVE_SOURCE_SEARCH: SKIP_NOT_IMPLEMENTED")
    print("C022_NATIVE_WINDOWS_GUI_CAPTURE_PASS")
    print("C022_NATIVE_SCREENSHOT_EVIDENCE: " + str(native_png))
    print("C022_NATIVE_TITLEBAR_OCR: SKIP_NOT_RUN")
    print("C022_FULL_V2_GUI: SKIP_NOT_IMPLEMENTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
