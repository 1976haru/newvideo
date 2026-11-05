"""C008 synthetic V1 -> staged V2 -> rollback tests. Never access user's D: drive."""
import json
from pathlib import Path
import sqlite3

import pytest

from nature_video_studio.migration import (
    V1_FIELDS, V2_SCHEMA_VERSION, MigrationBlocked,
    activate_migration, migration_state, prepare_migration,
    rollback_migration, sha256_file,
)


def legacy_fixture(path: Path, count=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    definitions = ", ".join(
        '"' + name + '" ' + ("NUMERIC" if name in ("width", "height", "duration") else "TEXT")
        for name in V1_FIELDS
    )
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE downloads (" + definitions + ")")
        for idx in range(count):
            row = (
                f"k{idx}", "commons", str(idx), f"冬の湖 {idx}", "한국어 작가",
                "https://example.org/source", "https://example.org/license",
                "CC BY", "not verified", 3840, 2160, 200.0, "lake",
                "[]", "D:/한글 영상/a.mp4", "sha256-unverified",
                "2026-01-01", "{}",
            )
            c.execute(
                "INSERT INTO downloads VALUES (" + ",".join("?" for _ in row) + ")",
                row,
            )


@pytest.fixture
def paths(tmp_path):
    source = tmp_path / "v1" / "library.sqlite3"
    dest = tmp_path / "v2" / "catalog.sqlite3"
    recovery = tmp_path / "recovery" / "C008"
    legacy_fixture(source)
    return source, dest, recovery


def test_original_v1_to_v2_then_rollback_preserves_source(paths):
    source, dest, recovery = paths
    before_sha = sha256_file(source)
    journal = prepare_migration(source, dest, recovery)
    assert not dest.exists(), "PREPARE must not install new DB"
    assert migration_state(journal) == "PREPARED"
    with pytest.raises(MigrationBlocked, match="consent"):
        activate_migration(journal)
    activate_migration(journal, user_approved=True)
    with sqlite3.connect(dest) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == V2_SCHEMA_VERSION
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT COUNT(*) FROM legacy_downloads").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 2
        assert conn.execute(
            "SELECT title,rights_review_status,original_duration_verified,"
            "file_verified,legacy_filepath FROM assets ORDER BY asset_id LIMIT 1"
        ).fetchone() == ("冬の湖 0", "GENERAL_REVIEW", 0, 0, "D:/한글 영상/a.mp4")
    with pytest.raises(MigrationBlocked, match="consent"):
        rollback_migration(journal)
    quarantined = rollback_migration(journal, user_approved=True)
    assert quarantined.exists() and not dest.exists()
    assert migration_state(journal) == "ROLLED_BACK"
    assert sha256_file(source) == before_sha


def test_existing_v2_user_data_survives_upgrade_and_rollback(paths):
    source, dest, recovery = paths
    dest.parent.mkdir(parents=True)
    with sqlite3.connect(dest) as conn:
        conn.execute("CREATE TABLE documents (note TEXT)")
        conn.execute("INSERT INTO documents VALUES ('keep existing V2 user work')")
        conn.execute("CREATE TABLE schema_migrations (migration_id TEXT PRIMARY KEY,"
                     "source_sha256 TEXT UNIQUE, imported_count INTEGER, applied_utc TEXT)")
        conn.execute("PRAGMA user_version = 1")
    original = dest.read_bytes()
    journal = prepare_migration(source, dest, recovery)
    assert dest.read_bytes() == original, "preparation must not mutate live V2 DB"
    activate_migration(journal, user_approved=True)
    with sqlite3.connect(dest) as conn:
        assert conn.execute("SELECT note FROM documents").fetchone()[0] == "keep existing V2 user work"
        assert conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 2
    quarantine = rollback_migration(journal, user_approved=True)
    assert quarantine.exists()
    with sqlite3.connect(dest) as conn:
        assert conn.execute("SELECT note FROM documents").fetchone()[0] == "keep existing V2 user work"
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_empty_legacy_db_is_valid(paths):
    source, dest, recovery = paths
    source.unlink()
    legacy_fixture(source, count=0)
    journal = prepare_migration(source, dest, recovery)
    activate_migration(journal, user_approved=True)
    with sqlite3.connect(dest) as conn:
        assert conn.execute("SELECT COUNT(*) FROM legacy_downloads").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0


def test_bad_legacy_schema_blocked_without_writes(paths):
    source, dest, recovery = paths
    with sqlite3.connect(source) as conn:
        conn.execute("ALTER TABLE downloads ADD COLUMN unexpected TEXT")
    with pytest.raises(MigrationBlocked, match="Unsupported legacy"):
        prepare_migration(source, dest, recovery)
    assert not dest.exists()


def test_corrupt_legacy_database_fails_closed(paths):
    source, dest, recovery = paths
    source.write_bytes(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        prepare_migration(source, dest, recovery)
    assert not dest.exists()


def test_missing_legacy_never_creates_source(paths):
    source, dest, recovery = paths
    source.unlink()
    with pytest.raises(MigrationBlocked, match="missing"):
        prepare_migration(source, dest, recovery)
    assert not source.exists()


def test_same_source_root_protected(paths):
    source, _, recovery = paths
    with pytest.raises(MigrationBlocked, match="overlaps original"):
        prepare_migration(source, source.parent / "catalog.sqlite3", recovery)


def test_unsupported_version_preserves_existing_v2(paths):
    source, dest, recovery = paths
    dest.parent.mkdir()
    with sqlite3.connect(dest) as conn:
        conn.execute("PRAGMA user_version=99")
    before = sha256_file(dest)
    with pytest.raises(MigrationBlocked, match="Unsupported current V2 schema"):
        prepare_migration(source, dest, recovery)
    assert sha256_file(dest) == before


def test_changed_live_v2_blocks_activation(paths):
    source, dest, recovery = paths
    dest.parent.mkdir()
    with sqlite3.connect(dest) as conn:
        conn.execute("CREATE TABLE schema_migrations (migration_id TEXT PRIMARY KEY,"
                     "source_sha256 TEXT UNIQUE, imported_count INTEGER, applied_utc TEXT)")
        conn.execute("CREATE TABLE notes (note TEXT)")
        conn.execute("PRAGMA user_version=1")
    journal = prepare_migration(source, dest, recovery)
    with sqlite3.connect(dest) as conn:
        conn.execute("INSERT INTO notes VALUES ('after prepare')")
    with pytest.raises(MigrationBlocked, match="changed"):
        activate_migration(journal, user_approved=True)
    assert migration_state(journal) == "PREPARED"


def test_change_after_activation_blocks_automatic_rollback(paths):
    source, dest, recovery = paths
    journal = prepare_migration(source, dest, recovery)
    activate_migration(journal, user_approved=True)
    with sqlite3.connect(dest) as conn:
        conn.execute("CREATE TABLE new_work (n TEXT)")
    with pytest.raises(MigrationBlocked, match="changed"):
        rollback_migration(journal, user_approved=True)
    assert migration_state(journal) == "ACTIVE_DB_CHANGED_NO_AUTO_ROLLBACK"


def test_interrupted_activation_is_blocked_and_recoverable(paths):
    source, dest, recovery = paths
    journal = prepare_migration(source, dest, recovery)
    data = json.loads(journal.read_text(encoding="utf-8"))
    data["status"] = "ACTIVATING"
    journal.write_text(json.dumps(data), encoding="utf-8")
    assert migration_state(journal) == "INTERRUPTED_BEFORE_PROMOTION_BLOCKED"
    Path(data["staged"]).replace(dest)
    assert migration_state(journal) == "INTERRUPTED_AFTER_PROMOTION_BLOCKED"
    quarantine = rollback_migration(journal, user_approved=True)
    assert quarantine.exists() and not dest.exists()


def test_duplicate_import_of_same_source_hash_is_rejected(paths):
    source, dest, recovery = paths
    journal = prepare_migration(source, dest, recovery)
    activate_migration(journal, user_approved=True)
    with pytest.raises(MigrationBlocked, match="already imported"):
        prepare_migration(source, dest, recovery)


def test_wal_sidecar_blocks_migration(paths):
    source, dest, recovery = paths
    fake = Path(str(source) + "-wal")
    fake.write_bytes(b"fixture")
    with pytest.raises(MigrationBlocked, match="journal/WAL"):
        prepare_migration(source, dest, recovery)
    assert fake.is_file() and not dest.exists()
