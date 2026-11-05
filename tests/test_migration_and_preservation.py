"""C012 mandatory preservation gate: synthetic DB/media, no real user paths/secrets."""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from types import SimpleNamespace

import pytest

from nature_video_studio.install_preservation import (
    UpdateBlocked, UpdateLocations, capture_preservation_baseline,
    install_versioned_program, verify_preservation,
)
from nature_video_studio.migration import (
    V1_FIELDS, activate_migration, prepare_migration, rollback_migration,
)


def _v1_database(path: Path) -> None:
    fields = ", ".join(
        '"' + col + '" ' + ("NUMERIC" if col in ("width", "height", "duration") else "TEXT")
        for col in V1_FIELDS
    )
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE downloads (" + fields + ")")
        row = (
            "lake-1", "commons", "42", "겨울 호수", "작가",
            "https://example.org/asset", "https://example.org/licence", "CC BY",
            "not yet reviewed", 3840, 2160, 199, "lake", "[]",
            "D:/영상/호수.mp4", "unverified", "2026-11-01", "{}",
        )
        db.execute("INSERT INTO downloads VALUES (" + ",".join("?" for _ in row) + ")", row)


def _v2_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA user_version=1")
        db.execute("CREATE TABLE user_notes (label TEXT)")
        db.execute("INSERT INTO user_notes VALUES ('do not erase')")
        db.execute("CREATE TABLE schema_migrations ("
                   "migration_id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL UNIQUE,"
                   "imported_count INTEGER NOT NULL, applied_utc TEXT NOT NULL)")


@pytest.fixture
def preservation_workspace(tmp_path):
    base = tmp_path / "테스트 한글 경로"
    v1app = base / "V1_1.0.2"
    v1data = base / "V1_사용자데이터"
    recovery = base / "V1_백업"
    v2app = base / "V2_프로그램"
    v2data = base / "V2_사용자데이터"
    package = base / "허용된_프로그램_패키지"

    for folder in (v1app, v1data, recovery, v2app, v2data, package):
        folder.mkdir(parents=True)
    (v1app / "V1_실행.cmd").write_text("REM stable legacy launcher", encoding="utf-8")
    _v1_database(v1data / "library.sqlite3")
    (v1data / "downloads").mkdir()
    (v1data / "downloads" / "호수.mp4").write_bytes(b"FAKE_V1_VIDEO_BYTES")
    (v1data / "cache").mkdir()
    (v1data / "cache" / "thumb.jpg").write_bytes(b"THUMB")
    (recovery / "C002_V1_0_2.zip").write_bytes(b"SYNTHETIC_RECOVERY_ARCHIVE")
    (recovery / "C004_DB").mkdir()
    shutil.copyfile(v1data / "library.sqlite3", recovery / "C004_DB" / "library_backup.sqlite3")
    _v2_database(v2data / "catalog.sqlite3")
    (v2data / "downloads").mkdir()
    (v2data / "downloads" / "새영상.mkv").write_bytes(b"FAKE_V2_MEDIA")
    (v2data / "settings.json").write_text('{"keep":true}', encoding="utf-8")
    old_release = v2app / "release-v2.0.0.dev0"
    old_release.mkdir()
    (old_release / "app.exe").write_bytes(b"ORIGINAL_PROGRAM_BINARY")
    (package / "sub").mkdir()
    (package / "sub" / "app.exe").write_bytes(b"NEW_PROGRAM_BINARY")
    (package / "README.txt").write_text("new release", encoding="utf-8")
    locations = UpdateLocations(
        v1_app=v1app, v1_data=v1data, recovery=recovery,
        v2_app=v2app, v2_data=v2data,
    )
    return locations, package


def test_migration_and_preservation_version_install_keeps_dbs_media_backups(preservation_workspace):
    locations, package = preservation_workspace
    before = capture_preservation_baseline(locations)
    old_program = (locations.v2_app / "release-v2.0.0.dev0" / "app.exe").read_bytes()
    release = install_versioned_program(package, locations, "v2.0.1")
    assert release == locations.v2_app / "release-v2.0.1"
    assert (release / "sub" / "app.exe").read_bytes() == b"NEW_PROGRAM_BINARY"
    assert (locations.v2_app / "release-v2.0.0.dev0" / "app.exe").read_bytes() == old_program
    verify_preservation(locations, before)
    assert before.files == capture_preservation_baseline(locations).files
    assert len(before.files["V1_DATA"]) > 0 and len(before.files["V2_DATA"]) > 0


def test_migration_and_preservation_v1_to_v2_then_program_upgrade_then_rollback(preservation_workspace):
    locations, package = preservation_workspace
    source = locations.v1_data / "library.sqlite3"
    target = locations.v2_data / "catalog.sqlite3"
    original_source = source.read_bytes()
    original_video = (locations.v1_data / "downloads" / "호수.mp4").read_bytes()
    journal = prepare_migration(source, target, locations.recovery / "C008")
    activate_migration(journal, user_approved=True)
    before = capture_preservation_baseline(locations)
    install_versioned_program(package, locations, "v2.0.2")
    verify_preservation(locations, before)
    with closing(sqlite3.connect(target)) as db:
        assert db.execute("PRAGMA user_version").fetchone() == (1,)
        assert db.execute("SELECT COUNT(*) FROM legacy_downloads").fetchone() == (1,)
        assert db.execute("SELECT label FROM user_notes").fetchone() == ("do not erase",)
    preserved_copy = rollback_migration(journal, user_approved=True)
    assert preserved_copy.exists()
    assert source.read_bytes() == original_source
    assert (locations.v1_data / "downloads" / "호수.mp4").read_bytes() == original_video
    with closing(sqlite3.connect(target)) as db:
        assert db.execute("SELECT label FROM user_notes").fetchone() == ("do not erase",)


@pytest.mark.parametrize("unsafe", [
    "same_v1", "nested_v1", "same_v2_data", "nested_recovery", "ancestor_of_v1",
])
def test_migration_and_preservation_rejects_unsafe_install_paths(preservation_workspace, unsafe):
    locations, package = preservation_workspace
    options = {
        "same_v1": locations.v1_app,
        "nested_v1": locations.v1_data / "embedded_program",
        "same_v2_data": locations.v2_data,
        "nested_recovery": locations.recovery / "install_here",
        "ancestor_of_v1": locations.v1_app.parent,
    }
    bad = UpdateLocations(
        locations.v1_app, locations.v1_data, locations.recovery,
        options[unsafe], locations.v2_data,
    )
    baseline = capture_preservation_baseline(locations)
    with pytest.raises(UpdateBlocked):
        install_versioned_program(package, bad, "v2.0.1")
    assert capture_preservation_baseline(locations) == baseline


@pytest.mark.parametrize("release_id", ["../escape", "..", ".", r"../V1", "", "/tmp", "V2/A"])
def test_migration_and_preservation_rejects_invalid_version_name(preservation_workspace, release_id):
    locations, package = preservation_workspace
    with pytest.raises(UpdateBlocked, match="release identifier"):
        install_versioned_program(package, locations, release_id)


def test_migration_and_preservation_refuses_existing_version_overwrite(preservation_workspace):
    locations, package = preservation_workspace
    before = capture_preservation_baseline(locations)
    old = locations.v2_app / "release-v2.0.0.dev0" / "app.exe"
    with pytest.raises(UpdateBlocked, match="already exists"):
        install_versioned_program(package, locations, "v2.0.0.dev0")
    assert old.read_bytes() == b"ORIGINAL_PROGRAM_BINARY"
    verify_preservation(locations, before)


def test_migration_and_preservation_blocks_unknown_v2_schema(preservation_workspace):
    locations, package = preservation_workspace
    target = locations.v2_data / "catalog.sqlite3"
    with closing(sqlite3.connect(target)) as db, db:
        db.execute("PRAGMA user_version=999")
    before = target.read_bytes()
    with pytest.raises(UpdateBlocked, match="schema is unsupported"):
        install_versioned_program(package, locations, "v2.0.3")
    assert target.read_bytes() == before
    assert not (locations.v2_app / "release-v2.0.3").exists()


@pytest.mark.parametrize("status", ["PREPARED", "ACTIVATING", "ROLLING_BACK", "UNKNOWN"])
def test_migration_and_preservation_blocks_pending_c008_migration(preservation_workspace, status):
    locations, package = preservation_workspace
    journal_dir = locations.recovery / "C008"
    journal_dir.mkdir()
    (journal_dir / "c008_fixture.json").write_text(
        json.dumps({"checklist": "C008", "status": status}), encoding="utf-8"
    )
    before = (locations.v1_data / "library.sqlite3").read_bytes()
    with pytest.raises(UpdateBlocked, match="migration"):
        install_versioned_program(package, locations, "v2.0.4")
    assert (locations.v1_data / "library.sqlite3").read_bytes() == before


def test_migration_and_preservation_blocks_corrupt_source_db(preservation_workspace):
    locations, package = preservation_workspace
    db = locations.v1_data / "library.sqlite3"
    db.write_bytes(b"CORRUPT_SIMULATED_DB")
    with pytest.raises(sqlite3.DatabaseError):
        install_versioned_program(package, locations, "v2.0.3")
    assert db.read_bytes() == b"CORRUPT_SIMULATED_DB"
    assert not (locations.v2_app / "release-v2.0.3").exists()


def test_migration_and_preservation_interrupted_copy_never_replaces_old_program(
    preservation_workspace, monkeypatch
):
    locations, package = preservation_workspace
    before = capture_preservation_baseline(locations)
    old = (locations.v2_app / "release-v2.0.0.dev0" / "app.exe").read_bytes()

    def fail_copy(*args, **kwargs):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(
        "nature_video_studio.install_preservation.shutil.copyfile", fail_copy
    )
    with pytest.raises(OSError, match="synthetic disk failure"):
        install_versioned_program(package, locations, "v2.0.5")
    assert not (locations.v2_app / "release-v2.0.5").exists()
    assert (locations.v2_app / "release-v2.0.0.dev0" / "app.exe").read_bytes() == old
    verify_preservation(locations, before)


def test_migration_and_preservation_detects_external_video_change_before_promotion(
    preservation_workspace, monkeypatch
):
    locations, package = preservation_workspace
    file = locations.v2_data / "downloads" / "새영상.mkv"
    original = file.read_bytes()
    from nature_video_studio import install_preservation as updater

    real_copy = updater.shutil.copyfile

    def external_change(src, dst):
        file.write_bytes(b"EXTERNAL_SIMULATED_CHANGE")
        return real_copy(src, dst)

    monkeypatch.setattr(updater.shutil, "copyfile", external_change)
    with pytest.raises(UpdateBlocked, match="changed"):
        install_versioned_program(package, locations, "v2.0.6")
    assert not (locations.v2_app / "release-v2.0.6").exists()
    assert original != file.read_bytes()  # We must NOT claim to auto-repair concurrent writes.


def test_migration_and_preservation_never_reads_or_deletes_keys(preservation_workspace, monkeypatch):
    locations, package = preservation_workspace
    called = []

    def forbidden(*args, **kwargs):
        called.append(args)
        raise AssertionError("credential access forbidden during installer update")

    monkeypatch.setitem(sys.modules, "keyring", SimpleNamespace(
        get_password=forbidden, set_password=forbidden, delete_password=forbidden,
    ))
    before = capture_preservation_baseline(locations)
    install_versioned_program(package, locations, "v2.0.7")
    verify_preservation(locations, before)
    assert called == []


def test_migration_and_preservation_no_implicit_v2_db_creation(preservation_workspace):
    locations, package = preservation_workspace
    target = locations.v2_data / "catalog.sqlite3"
    target.unlink()
    before = capture_preservation_baseline(locations)
    install_versioned_program(package, locations, "v2.0.8")
    assert not target.exists()
    verify_preservation(locations, before)


def test_migration_and_preservation_rejects_payload_symlink(preservation_workspace):
    locations, package = preservation_workspace
    link = package / "shortcut.py"
    try:
        link.symlink_to(locations.v1_data / "library.sqlite3")
    except (OSError, NotImplementedError):
        pytest.skip("OS did not allow symlink fixture")
    with pytest.raises(UpdateBlocked, match="linked"):
        install_versioned_program(package, locations, "v2.0.9")
    assert not (locations.v2_app / "release-v2.0.9").exists()
