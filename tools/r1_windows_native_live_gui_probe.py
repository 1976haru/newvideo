"""Native Windows UI proof that default V2 window wires REAL source adapter objects.

Does not click Search, contact providers, read credentials, or claim live API PASS.
This evidence is distinct from existing C022 disconnected baseline screenshots.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or sys.platform != "win32":
        print("R1_NATIVE_LIVE_GUI_SKIP_NOT_WINDOWS_OR_BAD_ARGS")
        return 2
    os.environ["QT_QPA_PLATFORM"] = "windows"
    from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QTabWidget
    from nature_video_studio.live_gui import LiveSearchTabsWidget
    from nature_video_studio.trial_gui import build_window
    from nature_video_studio.models import SearchMode
    from nature_video_studio.search_mode_state import LaneStatus

    app = QApplication.instance() or QApplication(["R1 native live provider screen"])
    if app.platformName().lower() != "windows":
        return 3
    window = build_window(live_providers=True)
    window.move(45, 45)
    window.show()
    for _ in range(8):
        app.processEvents()
    pane = window.findChild(LiveSearchTabsWidget, "trialSearchModes")
    if pane is None:
        return 4
    if [a.name for a in pane.coordinator._adapters] != [
        "Wikimedia Commons", "Pixabay"
    ]:
        return 5
    if not all([
        window.findChild(QTabWidget, "searchModeTabs"),
        window.findChild(QLineEdit, "pixabaySessionKey"),
        window.findChild(QLabel, "realProviderNotice"),
        window.findChild(QPushButton, "longSearchButton"),
        window.findChild(QPushButton, "shortSearchButton"),
        window.findChild(QLabel, "longProviderDetails"),
        window.findChild(QLabel, "shortProviderDetails"),
    ]):
        return 6
    if any(pane.session.lane(m).status != LaneStatus.NOT_SEARCHED for m in SearchMode):
        return 7
    handle = int(window.winId())
    if not handle or not ctypes.windll.user32.IsWindow(handle):
        return 8
    image = window.screen().grabWindow(handle)
    if image.isNull() or image.width() < 600 or image.height() < 400:
        return 9
    out = Path(args[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    screenshot = out / "r1_native_live_source_widgets.png"
    if not image.save(str(screenshot), "PNG"):
        return 10
    evidence = {
        "kind": "REAL_NATIVE_WINDOWS_QT_GUI_SOURCES_WIRED",
        "writable_user_data_access": False,
        "provider_names": ["Wikimedia Commons", "Pixabay"],
        "two_isolated_modes": True,
        "native_window_capture": screenshot.name,
        "provider_http_called": False,
        "saved_legacy_api_keys_accessed": False,
        "real_remote_api_search": "NOT_TESTED",
        "end_user_windows_test": "NOT_TESTED",
        "real_video_playback_download": "NOT_IMPLEMENTED",
    }
    (out / "r1_native_live_gui_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    window.close()
    app.processEvents()
    print("R1_NATIVE_LIVE_GUI_WIRING_PASS")
    print("R1_USER_PC_API_SEARCH: NOT_TESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
