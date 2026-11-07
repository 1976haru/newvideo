"""C022 CI quality gates, deliberately NOT proof of a native GUI screenshot.

This test runs on all headless CI runners to detect accidental removal of the
separate Windows GUI/EXE smoke job. Only the Windows native CI job can award
the C022 screenshot + trial packaged executable evidence.
"""
from __future__ import annotations

from pathlib import Path

import tools
from tools import c022_package_entry, c022_package_qa, c022_windows_gui_probe


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_c022_ci_contract_distinguishes_headless_and_native_windows_jobs():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "C011 Qt OFFSCREEN widget smoke (not native GUI)" in text
    assert "QT_QPA_PLATFORM: offscreen" in text
    assert "C022 Windows NATIVE GUI screenshot and trial EXE QA" in text
    assert "runs-on: windows-latest" in text
    assert "needs: [tests, c011-qt-windows]" in text
    assert "python -m tools.c022_windows_gui_probe" in text
    assert "python -m PyInstaller --noconfirm --clean --onedir" in text
    assert "python -m tools.c022_package_qa" in text
    assert "if: always()" in text
    assert "actions/upload-artifact@v4" in text
    assert "c022-windows-native-gui-and-trial-package-evidence" in text
    assert "--windowed" not in text  # Console smoke output is intentionally visible.


def test_c022_scripts_compile_without_gui_dependencies_on_headless_platforms():
    for script in (
        ROOT / "tools" / "c022_windows_gui_probe.py",
        ROOT / "tools" / "c022_package_entry.py",
        ROOT / "tools" / "c022_package_qa.py",
    ):
        compile(script.read_text(encoding="utf-8"), str(script), "exec")


def test_c022_trial_exe_entrypoint_only_allows_qa_commands(monkeypatch, capsys):
    # Main with unsupported parameters does not open GUI or start downloads.
    monkeypatch.setattr("sys.argv", ["package.exe", "--download", "https://example.org"])
    assert c022_package_entry.main() == 2
    assert "TRIAL_PACKAGE_ONLY" in capsys.readouterr().out


def test_c022_probe_on_non_windows_never_makes_a_false_gui_pass(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(c022_windows_gui_probe.sys, "platform", "linux")
    assert c022_windows_gui_probe.main([str(tmp_path / "native")]) == 3
    assert "SKIP_NOT_RUN" in capsys.readouterr().out
    assert not (tmp_path / "native").exists()


def test_c022_package_qa_on_non_windows_never_makes_a_false_exe_pass(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(c022_package_qa.sys, "platform", "linux")
    assert c022_package_qa.main([str(tmp_path / "missing.exe"), str(tmp_path)]) == 2
    assert "SKIP" in capsys.readouterr().out
    assert not (tmp_path / "missing.exe").exists()


def test_c022_native_capture_file_names_are_distinct_and_no_ocr_claim():
    text = (ROOT / "tools" / "c022_windows_gui_probe.py").read_text("utf-8")
    assert "c022_qt_client_capture.png" in text
    assert "c022_native_window_capture.png" in text
    assert "visible_native_titlebar_text_ocr" in text
    assert '"NOT_TESTED"' in text
    assert "C022_NATIVE_WINDOWS_GUI_CAPTURE_PASS" in text
    assert "real_search_download_preview_composer" in text


def test_c022_package_report_exposes_unverified_release_limitations():
    text = (ROOT / "tools" / "c022_package_qa.py").read_text("utf-8")
    assert "PYINSTALLER_ONEDIR_TRIAL_NOT_RELEASE" in text
    assert "real_python_absent_machine" in text
    assert "actual_installer_upgrade" in text
    assert "C022_FULL_NATURE_VIDEO_GUI: SKIP_NOT_IMPLEMENTED" in text
    assert "env.pop(\"PYTHONPATH\"" in text
    assert "env.pop(\"PYTHONHOME\"" in text
    assert "c022_package_evidence.json" in text
