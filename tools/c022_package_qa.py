"""C022 Windows PyInstaller *trial* package smoke: no PATH Python and Hangul path.

Read-only for all existing user files. Copies only CI-generated EXE payload
to a fresh temp folder, then launches the EXE without inheriting Python paths.
No real nature footage, downloader, updater or release installer is tested.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(exe: Path, arguments: list[str], sandbox: Path) -> str:
    env = dict(os.environ)
    windir = Path(env.get("SystemRoot") or r"C:\Windows")
    env["PATH"] = os.pathsep.join([
        str(windir / "System32"), str(windir), str(windir / "System32" / "Wbem")
    ])
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.pop("VIRTUAL_ENV", None)
    env["QT_QPA_PLATFORM"] = "windows"
    # Test-only app data stays under isolated runner temp, not user V1 paths.
    env["APPDATA"] = str(sandbox / "AppData" / "Roaming")
    env["LOCALAPPDATA"] = str(sandbox / "AppData" / "Local")
    env["USERPROFILE"] = str(sandbox / "MockUser")
    for key in ("APPDATA", "LOCALAPPDATA", "USERPROFILE"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    child = subprocess.run(
        [str(exe), *arguments], cwd=str(sandbox),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        env=env, timeout=120, check=False,
    )
    if child.returncode:
        # Do not print raw stdout; future unexpected errors may include URLs.
        raise RuntimeError("C022_PACKAGE_CHILD_FAILED: exit=" + str(child.returncode))
    return child.stdout


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or sys.platform != "win32":
        print("C022_WINDOWS_PACKAGE_QA_SKIP_BAD_ARGS_OR_PLATFORM")
        return 2
    original_exe, temp_root = map(Path, args)
    original_exe = original_exe.resolve(strict=True)
    if not original_exe.is_file() or original_exe.suffix.lower() != ".exe":
        print("C022_PACKAGE_QA_FAIL: missing input EXE")
        return 3
    source_dir = original_exe.parent
    if not (source_dir / "_internal").is_dir():
        print("C022_PACKAGE_QA_FAIL: onedir _internal missing")
        return 4
    temp_root = temp_root.resolve()
    package_dir = temp_root / "한글 공백 QA" / "실행 파일"
    if package_dir.exists():
        print("C022_PACKAGE_QA_FAIL: target already exists")
        return 5
    package_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, package_dir)
    test_exe = package_dir / original_exe.name
    if not test_exe.exists() or _sha256(test_exe) != _sha256(original_exe):
        print("C022_PACKAGE_QA_FAIL: EXE checksum differs")
        return 6
    smoke = _run(test_exe, ["--smoke"], temp_root)
    if "C011_GUI_SMOKE_PASS" not in smoke:
        print("C022_PACKAGE_QA_FAIL: EXE did not pass Qt trial smoke")
        return 7
    output_dir = temp_root / "packaged_native_gui"
    capture = _run(test_exe, ["--capture", str(output_dir)], temp_root)
    if "C022_NATIVE_WINDOWS_GUI_CAPTURE_PASS" not in capture:
        print("C022_PACKAGE_QA_FAIL: native EXE GUI screenshot unavailable")
        return 8
    report_file = output_dir / "c022_native_gui_evidence.json"
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if (
        report.get("platform") != "win32"
        or report.get("qpa_platform") != "windows"
        or not report.get("native_hwnd_present")
        or not report.get("window_visible")
        or not (output_dir / "c022_native_window_capture.png").is_file()
    ):
        print("C022_PACKAGE_QA_FAIL: evidence fields missing")
        return 9
    metadata = {
        "checklist": "C022",
        "package_kind": "PYINSTALLER_ONEDIR_TRIAL_NOT_RELEASE",
        "qt_native_windows_gui": "PASS",
        "package_smoke": "PASS",
        "python_on_child_path": False,
        "hangul_and_spaces_path": True,
        "trial_exe_sha256": _sha256(test_exe),
        "package_output_dir": "CI TEMP ONLY; NOT A RELEASE",
        "actual_installer_upgrade": "NOT_TESTED",
        "windows_10_11_end_user_qa": "NOT_TESTED",
        "real_search_download_preview_composer": "NOT_IMPLEMENTED",
        "full_gui_titlebar_ocr": "NOT_TESTED",
        "real_python_absent_machine": "NOT_TESTED",
    }
    output_dir.joinpath("c022_package_evidence.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("C022_WINDOWS_ONEDIR_TRIAL_PACKAGE_PASS")
    print("C022_WINDOWS_PACKAGED_NATIVE_GUI_PASS")
    print("C022_PYTHON_ABSENT_MACHINE: SKIP_NOT_TESTED")
    print("C022_INSTALLER_UPDATE: SKIP_NOT_IMPLEMENTED")
    print("C022_FULL_NATURE_VIDEO_GUI: SKIP_NOT_IMPLEMENTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
