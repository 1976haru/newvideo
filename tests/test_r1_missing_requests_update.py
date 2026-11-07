"""R1 Windows missing-requests regression: only existing V2 virtualenv may change.

These static gates complement the actual Windows scripted update/rollback smoke.
They do not claim a user's PC or real package installation was tested.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "tools" / "NVS_V2_Update_Existing.ps1"


def test_r1_missing_requests_v2_venv_preflight_before_source_swap():
    script = UPDATER.read_text(encoding="utf-8")
    assert "function EnsureLiveDependencies" in script
    assert "import requests, keyring" in script
    assert "'requests>=2.32,<3'" in script
    assert "'keyring>=25,<27'" in script
    assert "--no-cache-dir" in script
    assert "--isolated" in script
    assert "NVS_V2_INSTALL_LIVE_DEPS_EXISTING_VENV_ONLY" in script
    assert "NVS_V2_BLOCKED_LIVE_DEPENDENCY_INSTALL" in script
    assert "NVS_V2_BLOCKED_LIVE_DEPENDENCY_IMPORT" in script
    assert ".venv\\Scripts\\python.exe" in script

    assert script.index("EnsureLiveDependencies $python") < script.index(
        "RunSmoke $python $stage -RequireC024")
    assert script.index("RunSmoke $python $stage -RequireC024") < script.index(
        "Move-Item -LiteralPath $active -Destination $backup")
    assert "if (!$FixtureMode -and" in script
    assert "src.nvs-backup-" in script
    assert "NVS_V2_AUTOMATIC_SOURCE_ROLLBACK_PASS" in script


def test_r1_existing_v1_data_paths_untouched_by_dep_repair():
    script = UPDATER.read_text(encoding="utf-8")
    body = script.split("function EnsureLiveDependencies", 1)[1].split(
        "function RunSmoke", 1)[0]
    assert "pip" in body and "requests" in body and "keyring" in body
    assert "D:\\NatureVideoStudio" not in body
    assert "NatureVideoStudio_2026" not in body
    assert "set_password" not in body and "delete_password" not in body
    assert "Get-Content" not in body and "Remove-Item" not in body


def test_r1_dependency_targets_declared_in_pyproject():
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dependencies = ["requests>=2.32,<3"]' in project
    assert '"keyring>=25,<27"' in project
