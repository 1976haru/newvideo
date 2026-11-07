"""C022 *trial-only* PyInstaller entrypoint for Windows packaging QA.

This is not the real Nature Video Studio Windows release, updater or installer.
It only packages the existing, clearly labeled V2 Qt trial version-identity GUI.
"""
from __future__ import annotations

import sys


def main() -> int:
    args = list(sys.argv[1:])
    if args == ["--smoke"]:
        from nature_video_studio.trial_gui import main as trial
        return trial(["--smoke"])
    if len(args) == 2 and args[0] == "--capture":
        from tools.c022_windows_gui_probe import main as probe
        return probe([args[1]])
    print("C022_TRIAL_PACKAGE_ONLY: --smoke or --capture <evidence-folder>")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
