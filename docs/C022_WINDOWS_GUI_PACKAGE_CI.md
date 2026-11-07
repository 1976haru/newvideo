# C022 — Windows native GUI screenshot + trial EXE package CI

**Status:** Implementation and GitHub Actions proof in progress. **Do not claim PASS from existing offscreen unit tests.** The original C022 checklist gate is 3 points. The goal is to separate Python mock tests, offscreen Qt widget checks, actual Windows native GUI window screenshot, and a trial-only packaged executable smoke test. Full product GUI and release installer are OUT OF SCOPE.

## Existing versus new acceptance evidence

| Evidence | Platform/method | What it establishes | What it does NOT establish |
| --- | --- | --- | --- |
| Core pytest | Windows/Ubuntu Python 3.11/3.12 | Headless code-level tests | Window, screenshot, package |
| Existing C011 | Qt OFFSCREEN plugin on Windows; window widget and --smoke checks | Qt widgets/labels and version logic | Native Windows titlebar/window visibility |
| C022 native UI | Windows platform plugin, QApplication visible window and Win32 HWND, QScreen.grabWindow(HWND), PNG and JSON hash | Actual Qt trial window is shown and pixels are captured on Windows CI | OCR of OS titlebar text; Win10/11 physical user PC |
| C022 onedir package | PyInstaller builds trial EXE, runs EXE --smoke and EXE --capture from a copied Korean/spaces folder with Python removed from child PATH | Trial EXE can execute on hosted Windows runner with no Python on child PATH and can capture native GUI | Python absent from actual computer; Windows installer/upgrade; full V2 search/player/download |

### Files and commands

- Windows native GUI probe: tools/c022_windows_gui_probe.py
- Trial-only PyInstaller entrypoint: tools/c022_package_entry.py
- Packaged EXE runner and SHA validation: tools/c022_package_qa.py
- Headless CI contract test (NOT proof of native GUI): tests/test_c022_ci_contract.py
- CI configuration: .github/workflows/ci.yml

Exact targeted commands:

    python -m pytest -q tests/test_c022_ci_contract.py
    python -m tools.c022_windows_gui_probe <runner-temp-source>
    python -m PyInstaller --noconfirm --clean --onedir --name NVS_V2_C022_TRIAL --paths src --paths . tools/c022_package_entry.py
    python -m tools.c022_package_qa dist/NVS_V2_C022_TRIAL/NVS_V2_C022_TRIAL.exe <runner-temp-package>
    python -m pytest -q

The Windows job installs PySide6==6.12.0 and PyInstaller==6.16.0, runs ONLY on windows-latest and depends on successful core test matrix and C011 offscreen Qt tests. The native probe actively REJECTS QT_QPA_PLATFORM=offscreen or minimal. The executable is a version-labeled C022 QA trial (v2.0.0.dev0), not a full product or installer. Child EXE runs with PYTHONPATH/PYTHONHOME/VIRTUAL_ENV removed and a PATH consisting only of Windows system folders. This is NOT equivalent to a physical Windows computer without Python installed.

### Evidence artifacts and handling

GitHub Actions upload-artifact retains (14 days) a bundle named c022-windows-native-gui-and-trial-package-evidence, including:

- c022_source_native/c022_native_window_capture.png — QScreen capture by native HWND
- c022_source_native/c022_qt_client_capture.png — client area only; not the OS titlebar
- c022_source_native/c022_native_gui_evidence.json — window title, QWidget label validation, Windows QPA, HWND, screenshot checksums and dimensions
- c022_package_qa/packaged_native_gui/c022_native_window_capture.png — screenshot from actual packaged EXE
- c022_package_qa/packaged_native_gui/c022_package_evidence.json — package SHA, Python PATH isolation, Korean/spaces path and clear trial-only limitations

A missing, blank or invalid native screenshot fails the Windows job. Neither screenshot has OCR verification of titlebar text, and the report explicitly says NOT_TESTED. Actual user desktop titlebar visual confirmation for C011 was performed separately.

### Gate and remaining risk

Only call C022 3/3 PASS after verifying (1) Windows native QScreen screenshot with HWND and GUI text, (2) independent PyInstaller onedir EXE build and native EXE smoke/capture under a Hangul path, and (3) published PNG/JSON proof and passing Windows workflow. Headless unit tests or offscreen Qt widget tests alone NEVER satisfy C022.

Open gates beyond C022: real Win10/11 Python-absent VM install and EXE run; licensed sample download and source thumbnail rendering; playable local MP4 pause/seek; actual user V1 database/keys preservation after installer/updater (C012), QtMultimedia/FFmpeg packed binaries, disk-space/antivirus/Defender testing, formal release signatures/manifests. C022 does not authorize claiming any of these are complete.

Security: CI uses temporary runner paths only, no actual user media, D: data, V1 program, API keys or downloaded copyrighted videos. No main push/merge. Work stays on feature/v2-research-rebuild with Draft PR #1.
