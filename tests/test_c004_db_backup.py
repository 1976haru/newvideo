"""Offline audit tests using isolated fixture databases; no user files accessed."""
import json
from pathlib import Path
import sqlite3

import pytest

from tools.audit_v102_db import backup_library, sha256_file


def make_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE downloads (id INTEGER PRIMARY KEY, title TEXT)")
        conn.execute("INSERT INTO downloads (title) VALUES ('PRIVATE SAMPLE TITLE')")
        conn.execute("CREATE TABLE metadata (key TEXT, value TEXT)")
        conn.execute("INSERT INTO metadata VALUES ('api_token', 'SECRET SHOULD NEVER EXPORT')")
        conn.commit()


def test_consistent_snapshot_and_nonmutation(tmp_path):
    source = tmp_path / "user" / "library.sqlite3"
    source.parent.mkdir()
    make_db(source)
    original_hash = sha256_file(source)
    result = backup_library(source, tmp_path / "safe" / "C004_DB")
    assert result["integrity_check"] == "ok"
    assert result["source_sha256_before"] == result["source_sha256_after"] == original_hash
    assert sha256_file(source) == original_hash
    assert result["backup_sha256"] == sha256_file(Path(result["backup"]))
    assert {t["table"]: t["rows"] for t in result["tables"]} == {"downloads": 1, "metadata": 1}
    with sqlite3.connect(result["backup"]) as copy:
        assert copy.execute("SELECT title FROM downloads").fetchone()[0] == "PRIVATE SAMPLE TITLE"


def test_manifest_has_only_counts_and_columns_not_row_values(tmp_path):
    original = tmp_path / "library.sqlite3"
    make_db(original)
    result = backup_library(original, tmp_path / "backups")
    text = Path(result["manifest_path"]).read_text(encoding="utf-8")
    manifest = json.loads(text)
    assert manifest["status"] == "PASS"
    assert "PRIVATE SAMPLE TITLE" not in text
    assert "SECRET SHOULD NEVER EXPORT" not in text
    assert "downloads" in text


def test_multiple_runs_do_not_overwrite_backups(tmp_path):
    original = tmp_path / "library.sqlite3"
    make_db(original)
    one = backup_library(original, tmp_path / "backups")
    two = backup_library(original, tmp_path / "backups")
    assert one["backup"] != two["backup"]
    assert Path(one["backup"]).exists()
    assert Path(two["backup"]).exists()


def test_no_source_db_ever_created_when_missing(tmp_path):
    source = tmp_path / "missing" / "library.sqlite3"
    with pytest.raises(FileNotFoundError):
        backup_library(source, tmp_path / "backups")
    assert not source.exists()


def test_backup_source_folder_must_be_different(tmp_path):
    source = tmp_path / "library.sqlite3"
    make_db(source)
    with pytest.raises(ValueError):
        backup_library(source, tmp_path)
    assert sha256_file(source)


def test_corrupt_source_not_pass(tmp_path):
    source = tmp_path / "library.sqlite3"
    source.write_bytes(b"INVALID SOURCE DB")
    with pytest.raises(sqlite3.DatabaseError):
        backup_library(source, tmp_path / "backup")
    assert source.read_bytes() == b"INVALID SOURCE DB"


def test_empty_db_rejected(tmp_path):
    source = tmp_path / "library.sqlite3"
    source.touch()
    with pytest.raises(ValueError):
        backup_library(source, tmp_path / "backup")
