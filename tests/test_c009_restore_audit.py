"""C009 tests: fake Windows credential backend, synthetic ZIP/DB only.

No Windows vault access, no real API keys, no network or user-file changes.
"""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from tools import audit_c009_windows as audit


def make_archive(directory: Path):
    path = directory / "legacy_V1_0_2.zip"
    with ZipFile(path, "w") as handle:
        handle.writestr(
            "NatureVideoStudio/nvs/gui.py",
            """from nvs.credentials import read_key, save_key
def start():
    read_key('pexels')
    read_key("pixabay")
    read_key('DO_NOT_PRINT_PRIVATE_KEY_123')
    save_key('pexels', 'a private thing')
""",
        )
        handle.writestr(
            "NatureVideoStudio/nvs/credentials.py",
            """SERVICE = 'NatureVideoStudio_2026'
import keyring
def read_key(provider):
    return keyring.get_password(SERVICE, provider)
""",
        )
    return path


def test_account_names_are_derived_without_running_v1_code(tmp_path):
    archive = make_archive(tmp_path)
    assert audit.source_account_ids(archive) == ("pexels", "pixabay")


def test_read_status_returns_presence_only_not_secret():
    secret = "DO_NOT_ECHO_MY_REAL_KEY_0123456789"
    calls = []

    def lookup(service, account):
        calls.append((service, account))
        return secret if account == "pexels" else None

    out = io.StringIO()
    with redirect_stdout(out):
        state, statuses = audit.key_status(("pexels", "pixabay"), lookup)
    assert state == "CHECKED_MASKED"
    assert statuses == {"pexels": "PRESENT", "pixabay": "ABSENT"}
    assert calls == [(audit.SERVICE, "pexels"), (audit.SERVICE, "pixabay")]
    assert secret not in repr(statuses) and secret not in out.getvalue()


def test_backend_exception_is_redacted_even_when_it_contains_a_secret():
    def lookup(service, account):
        raise RuntimeError("THE_SECRET_WOULD_HAVE_BEEN_HERE")

    state, statuses = audit.key_status(("pexels",), lookup)
    assert state == "CHECKED_MASKED"
    assert statuses == {"pexels": "ACCESS_ERROR"}
    assert "THE_SECRET_WOULD_HAVE_BEEN_HERE" not in repr(statuses)


def test_no_key_names_causes_no_vault_access():
    def forbidden(*args):
        raise AssertionError("Must not enumerate or probe unknown usernames")

    state, statuses = audit.key_status((), forbidden)
    assert state == "ACCOUNT_NAMES_UNRESOLVED"
    assert statuses == {}


def test_verified_zip_and_c004_snapshot_does_not_change_sources(tmp_path, monkeypatch):
    zip_file = make_archive(tmp_path)
    monkeypatch.setattr(audit, "TRUSTED_ZIP_SHA256", audit.sha256_file(zip_file))
    backup = tmp_path / "backup" / "library.sqlite3"
    backup.parent.mkdir()
    backup.write_bytes(b"a fake saved C004 file")
    monkeypatch.setattr(audit, "TRUSTED_C004_SHA256", audit.sha256_file(backup))

    app = tmp_path / "V1_APP"
    app.mkdir()
    (app / "START_NATURE_VIDEO_STUDIO.cmd").write_text("@echo off\n", encoding="ascii")
    root = tmp_path / "V1_DATA"
    root.mkdir()
    database = root / "library.sqlite3"
    database.write_bytes(b"not for real SQLite access")
    original_source = database.read_bytes()
    original_backup = backup.read_bytes()

    snapshot = audit.snapshot(
        archive=zip_file,
        app_folder=app,
        c004_backup=backup,
        root=str(root),
        root_source="DEFAULT_CANDIDATE",
        lookup=lambda service, account: "fake" if account == "pexels" else "also_fake",
    )
    assert snapshot["root_exists"] and snapshot["db_exists"]
    assert snapshot["launcher_exists"]
    assert snapshot["c002_sha256_ok"] and snapshot["c004_sha256_ok"]
    assert snapshot["key_status"] == {"pexels": "PRESENT", "pixabay": "PRESENT"}
    assert database.read_bytes() == original_source
    assert backup.read_bytes() == original_backup
    out = io.StringIO()
    with redirect_stdout(out):
        audit.report(snapshot)
    assert "KEY_PEXELS: PRESENT" in out.getvalue()
    assert "fake" not in out.getvalue()


def test_assessment_matches_stable_v1_without_false_v2_claim():
    d = {
        "root": r"D:\NatureVideoStudio",
        "db_sha256": "AA",
        "providers": ["pexels"],
        "key_status": {"pexels": "PRESENT"},
        "app_exists": True,
        "launcher_exists": True,
        "root_exists": True,
        "db_exists": True,
        "c002_sha256_ok": True,
        "c004_sha256_ok": True,
    }
    verdict, checks = audit.assess(d, d.copy())
    assert verdict == "V1_RESTORE_BASELINE_PASS"
    assert all(line.endswith("MATCH") for line in checks)
    assert "V2" not in verdict


@pytest.mark.parametrize("update,expected", [
    ({"db_sha256": "CHANGED"}, "REVIEW_CHANGED_STATE"),
    ({"root": r"E:\Other"}, "REVIEW_CHANGED_STATE"),
    ({"key_status": {"pexels": "ABSENT"}}, "REVIEW_CHANGED_STATE"),
    ({"db_exists": False}, "REVIEW_MISSING_PATH"),
    ({"key_status": {}}, "REVIEW_KEY_UNVERIFIED"),
])
def test_changed_or_missing_evidence_does_not_pass(update, expected):
    baseline = {
        "root": r"D:\NatureVideoStudio", "db_sha256": "abc",
        "providers": ["pexels"], "key_status": {"pexels": "PRESENT"},
        "app_exists": True, "root_exists": True, "db_exists": True,
        "c002_sha256_ok": True, "c004_sha256_ok": True,
    }
    after = dict(baseline)
    after.update(update)
    verdict, _ = audit.assess(baseline, after)
    assert verdict == expected


def test_invalid_zip_sha_rejected_before_vault_lookup(tmp_path, monkeypatch):
    archive = make_archive(tmp_path)
    monkeypatch.setattr(audit, "TRUSTED_ZIP_SHA256", "0" * 64)
    backup = tmp_path / "backup.sqlite3"
    backup.write_bytes(b"test")
    with pytest.raises(RuntimeError, match="C002 SHA256"):
        audit.snapshot(
            archive=archive, app_folder=tmp_path,
            c004_backup=backup, root=str(tmp_path),
            root_source="DEFAULT_CANDIDATE",
            lookup=lambda *args: (_ for _ in ()).throw(AssertionError("Vault touched!")),
        )


def test_baseline_payload_has_no_secret_value():
    saved = {
        "root": r"D:\NatureVideoStudio", "db_sha256": "abc",
        "providers": ["pexels"], "key_status": {"pexels": "PRESENT"},
    }
    serialized = json.dumps(saved)
    assert "PRESENT" in serialized
    assert "password" not in serialized.lower()
