"""C010 rollback readiness uses mock V1 state and must not claim actual V2 failure."""
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from tools import audit_c010_rollback as c010


def make_state():
    return {
        "checklist": "C009",
        "root": r"D:\NatureVideoStudio",
        "root_source": "DEFAULT_CANDIDATE",
        "db_sha256": "FAKE_DB_DIGEST",
        "providers": ["pexels", "pixabay"],
        "key_status": {"pexels": "PRESENT", "pixabay": "PRESENT"},
        "keyring_check": "CHECKED_MASKED",
        "app_exists": True,
        "launcher_exists": True,
        "root_exists": True,
        "db_exists": True,
        "c002_sha256_ok": True,
        "c004_sha256_ok": True,
    }


def test_readiness_only_never_claims_completed_v2_rollback():
    state = make_state()
    verdict, checks = c010.assess_fallback(state, state.copy())
    assert verdict == "C010_V1_FALLBACK_READINESS_PASS_ONLY"
    assert all(check.endswith("MATCH") for check in checks)
    assert "V2" not in verdict and "ROLLBACK_PASS" not in verdict


@pytest.mark.parametrize("field,value", [
    ("root", r"E:\Other"), ("db_sha256", "CHANGED"),
    ("providers", ["pexels"]), ("key_status", {"pexels": "ABSENT"}),
    ("c002_sha256_ok", False), ("c004_sha256_ok", False),
])
def test_changes_or_backups_tampering_block_fallback(field, value):
    baseline = make_state()
    current = make_state()
    current[field] = value
    verdict, checks = c010.assess_fallback(baseline, current)
    assert verdict == "C010_REVIEW_LEGACY_STATE_CHANGED"
    assert any(line.endswith("CHANGED") for line in checks)


@pytest.mark.parametrize("field", ["app_exists", "launcher_exists", "root_exists", "db_exists"])
def test_missing_v1_install_or_data_blocks(field):
    baseline = make_state()
    current = make_state()
    current[field] = False
    verdict, _ = c010.assess_fallback(baseline, current)
    assert verdict == "C010_REVIEW_V1_PATH_MISSING"


@pytest.mark.parametrize("check", ["KEYRING_PYTHON_MODULE_MISSING", "ACCOUNT_NAMES_UNRESOLVED"])
def test_keyring_backend_not_verified_is_not_pass(check):
    baseline = make_state()
    current = make_state()
    current["keyring_check"] = check
    verdict, _ = c010.assess_fallback(baseline, current)
    assert verdict == "C010_REVIEW_KEYRING_NOT_CHECKED"


def test_empty_credentials_cannot_pass_even_if_prior_snapshot_empty():
    state = make_state()
    state["key_status"] = {}
    verdict, _ = c010.assess_fallback(state, state.copy())
    assert verdict == "C010_REVIEW_LEGACY_KEYS_UNVERIFIED"


def test_readonly_auditor_with_mock_v1_and_fake_keys(tmp_path):
    baseline = make_state()
    baseline_path = tmp_path / "C009_baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    before_bytes = baseline_path.read_bytes()
    calls = []

    def snapshot(**kw):
        calls.append(kw)
        return make_state()

    fake = SimpleNamespace(
        DEFAULT_ZIP_FOLDER=tmp_path,
        DEFAULT_V1_APP=tmp_path / "existing_v1_program",
        DEFAULT_C004_BACKUP=tmp_path / "existing_v1_backup.sqlite3",
        find_trusted_zip=lambda folder: tmp_path / "original.zip",
        windows_root=lambda: (r"D:\NatureVideoStudio", "DEFAULT_CANDIDATE"),
        snapshot=snapshot,
    )
    verdict, checks, current = c010.run_with_auditor(fake, baseline_path)
    assert verdict == "C010_V1_FALLBACK_READINESS_PASS_ONLY"
    assert calls[0]["root"] == r"D:\NatureVideoStudio"
    assert len(checks) == 5
    assert current["key_status"] == {"pexels": "PRESENT", "pixabay": "PRESENT"}
    assert baseline_path.read_bytes() == before_bytes
    assert sorted(tmp_path.iterdir()) == [baseline_path]


def test_missing_baseline_refuses_to_invent_one(tmp_path):
    fake = SimpleNamespace()
    verdict, checks, current = c010.run_with_auditor(fake, tmp_path / "not_found.json")
    assert verdict == "C010_BLOCKED_C009_BASELINE_NOT_FOUND"
    assert checks == () and current == {}
    assert not (tmp_path / "not_found.json").exists()


def test_tampered_baseline_schema_blocked(tmp_path):
    p = tmp_path / "baseline.json"
    p.write_text('{"checklist": "C010", "db_sha256": "abc"}', encoding="utf-8")
    verdict, _, _ = c010.run_with_auditor(SimpleNamespace(), p)
    assert verdict == "C010_BLOCKED_INVALID_BASELINE"


def test_cli_error_does_not_echo_raw_exception(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(c010.sys, "platform", "win32")
    missing = tmp_path / "missing_c009.py"
    rc = c010.main(["--c009-script", str(missing)])
    out = capsys.readouterr().out
    assert rc != 0
    assert "C010_AUDIT_ERROR" in out
    assert "SECRET_VALUES_PRINTED" not in out
    assert "V2_TO_V1_GUI_ROLLBACK_TEST: SKIP_NOT_RUN" in out
    assert "===== C010 REPORT END =====" in out


def test_cli_unavailable_non_windows_does_not_attempt_vault(monkeypatch, capsys):
    monkeypatch.setattr(c010.sys, "platform", "linux")
    assert c010.main([]) == 2
    out = capsys.readouterr().out
    assert "C010_BLOCKED_WINDOWS_ONLY" in out
    assert "===== C010 REPORT END =====" in out
