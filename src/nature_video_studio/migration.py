"""C008: staged V1->V2 migration prototype. No automatic user-data writes."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4

V2_SCHEMA_VERSION = 1
V1_FIELDS = (
    "item_key", "source", "source_id", "title", "creator", "page_url",
    "license_url", "license_status", "license_note", "width", "height",
    "duration", "category", "tags_json", "filepath", "sha256",
    "downloaded_at", "probe_json",
)
V1_COLUMN_SQL = ", ".join('"' + field + '"' for field in V1_FIELDS)


class MigrationBlocked(RuntimeError):
    """Refuse a migration when preservation is not guaranteed."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _readonly(path: Path):
    if not path.is_file():
        raise MigrationBlocked("SQLite source is missing; nothing will be created")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def _verify(conn: sqlite3.Connection):
    if [r[0] for r in conn.execute("PRAGMA integrity_check")] != ["ok"]:
        raise MigrationBlocked("SQLite integrity_check FAILED")
    if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise MigrationBlocked("SQLite foreign keys FAILED")


def _no_sidecars(path: Path):
    for ext in ("-wal", "-shm", "-journal"):
        if Path(str(path) + ext).exists():
            raise MigrationBlocked("SQLite has journal/WAL files: close the application")


def _safe_paths(source: Path, target: Path, recovery: Path):
    source, target, recovery = (
        x.resolve(strict=False) for x in (source, target, recovery)
    )
    if target == source or target.is_relative_to(source.parent):
        raise MigrationBlocked("Target overlaps original V1 data")
    if recovery == source or recovery.is_relative_to(source.parent):
        raise MigrationBlocked("Recovery overlaps original V1 data")
    if recovery == target or recovery.is_relative_to(target.parent) or target.is_relative_to(recovery):
        raise MigrationBlocked("Recovery and V2 data cannot overlap")


def _write_journal(path: Path, value: dict):
    temp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("checklist") != "C008":
        raise MigrationBlocked("Not a C008 journal")
    return data


def _legacy_rows(conn: sqlite3.Connection) -> list[tuple]:
    _verify(conn)
    found = {r[1] for r in conn.execute("PRAGMA table_info(downloads)")}
    if found != set(V1_FIELDS):
        raise MigrationBlocked("Unsupported legacy downloads schema")
    rows = conn.execute(
        "SELECT " + V1_COLUMN_SQL + " FROM downloads ORDER BY item_key"
    ).fetchall()
    keys = [row[0] for row in rows]
    if any(not isinstance(k, str) or not k for k in keys) or len(set(keys)) != len(keys):
        raise MigrationBlocked("Invalid or duplicate legacy item keys")
    return rows


def _v2_schema(conn: sqlite3.Connection):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, V2_SCHEMA_VERSION):
        raise MigrationBlocked("Unsupported V2 schema version")
    if version == 0 and conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchone():
        raise MigrationBlocked("Unversioned nonempty DB cannot be upgraded")
    conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        migration_id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL UNIQUE,
        imported_count INTEGER NOT NULL, applied_utc TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS assets (
        asset_id TEXT PRIMARY KEY, source TEXT, source_id TEXT,
        title TEXT, creator TEXT, source_url TEXT, width NUMERIC,
        height NUMERIC, duration_seconds NUMERIC,
        original_duration_verified INTEGER NOT NULL DEFAULT 0,
        rights_review_status TEXT NOT NULL DEFAULT 'GENERAL_REVIEW',
        legacy_license_status TEXT,
        file_verified INTEGER NOT NULL DEFAULT 0, legacy_filepath TEXT)""")
    col_defs = ", ".join(
        '"' + col + '" ' + ("NUMERIC" if col in ("width", "height", "duration") else "TEXT")
        for col in V1_FIELDS
    )
    conn.execute("CREATE TABLE IF NOT EXISTS legacy_downloads (" + col_defs +
                 ', PRIMARY KEY("item_key"))')
    conn.execute("PRAGMA user_version=1")


def _insert_legacy(conn: sqlite3.Connection, rows: list[tuple], source_sha: str, migration_id: str):
    for row in rows:
        v = dict(zip(V1_FIELDS, row))
        conn.execute(
            "INSERT INTO legacy_downloads (" + V1_COLUMN_SQL + ") VALUES (" +
            ",".join("?" for _ in V1_FIELDS) + ")", row
        )
        conn.execute("""INSERT INTO assets (
            asset_id, source, source_id, title, creator, source_url,
            width, height, duration_seconds, original_duration_verified,
            rights_review_status, legacy_license_status, file_verified,
            legacy_filepath) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "legacy-v1:" + v["item_key"], v["source"], v["source_id"],
                v["title"], v["creator"], v["page_url"], v["width"],
                v["height"], v["duration"], 0, "GENERAL_REVIEW",
                v["license_status"], 0, v["filepath"],
            ),
        )
    conn.execute(
        "INSERT INTO schema_migrations VALUES (?,?,?,?)",
        (migration_id, source_sha, len(rows), datetime.now(timezone.utc).isoformat()),
    )


def prepare_migration(source: Path, target: Path, recovery: Path) -> Path:
    """Prepare transaction and verified snapshots, without changing live target."""
    source, target, recovery = map(Path, (source, target, recovery))
    _safe_paths(source, target, recovery)
    _no_sidecars(source)
    _no_sidecars(target)
    if not source.is_file():
        raise MigrationBlocked("V1 source database missing")
    source_hash = sha256_file(source)
    before_hash = sha256_file(target) if target.is_file() else None
    migration_id = uuid4().hex
    staged = target.parent / (".c008_" + migration_id + ".staging.sqlite3")
    previous = recovery / ("v2_before_" + migration_id + ".sqlite3") if before_hash else None
    manifest = recovery / ("c008_" + migration_id + ".json")

    with closing(_readonly(source)) as original:
        rows = _legacy_rows(original)
    if before_hash:
        with closing(_readonly(target)) as old:
            _verify(old)
            if old.execute("PRAGMA user_version").fetchone()[0] != V2_SCHEMA_VERSION:
                raise MigrationBlocked("Unsupported current V2 schema")
            try:
                duplicate = old.execute(
                    "SELECT 1 FROM schema_migrations WHERE source_sha256=?",
                    (source_hash,),
                ).fetchone()
            except sqlite3.DatabaseError as exc:
                raise MigrationBlocked("V2 migration registry missing") from exc
            if duplicate:
                raise MigrationBlocked("Same legacy revision already imported")
    target.parent.mkdir(parents=True, exist_ok=True)
    recovery.mkdir(parents=True, exist_ok=True)
    try:
        if before_hash:
            with closing(_readonly(target)) as old:
                with closing(sqlite3.connect(staged)) as tmp:
                    old.backup(tmp)
            with closing(_readonly(target)) as old:
                with closing(sqlite3.connect(previous)) as saved:
                    old.backup(saved)
            with closing(_readonly(previous)) as saved:
                _verify(saved)
            if sha256_file(target) != before_hash:
                raise MigrationBlocked("Target modified during snapshot")
        else:
            with closing(sqlite3.connect(staged)) as tmp:
                pass

        with closing(sqlite3.connect(staged)) as tmp:
            tmp.execute("BEGIN IMMEDIATE")
            try:
                _v2_schema(tmp)
                _insert_legacy(tmp, rows, source_hash, migration_id)
                tmp.commit()
            except Exception:
                tmp.rollback()
                raise
            _verify(tmp)
            count = tmp.execute(
                "SELECT imported_count FROM schema_migrations WHERE migration_id=?",
                (migration_id,),
            ).fetchone()
            if count != (len(rows),):
                raise MigrationBlocked("Import record count check failed")
        if sha256_file(source) != source_hash:
            raise MigrationBlocked("V1 source changed during migration")
        if before_hash and sha256_file(target) != before_hash:
            raise MigrationBlocked("Existing V2 target changed during migration")
        info = {
            "checklist": "C008", "status": "PREPARED", "id": migration_id,
            "source_sha256": source_hash, "source_record_count": len(rows),
            "target": str(target.resolve(strict=False)),
            "before_sha256": before_hash, "new_sha256": sha256_file(staged),
            "staged": str(staged), "previous": str(previous) if previous else None,
            "previous_sha256": sha256_file(previous) if previous else None,
        }
        _write_journal(manifest, info)
        return manifest
    except Exception:
        if staged.exists():
            staged.unlink()  # Only our disposable temp file; never original user data.
        raise


def activate_migration(journal: Path, *, user_approved: bool = False):
    if not user_approved:
        raise MigrationBlocked("Explicit user consent needed for activation")
    path = Path(journal)
    info = _load(path)
    if info["status"] != "PREPARED":
        raise MigrationBlocked("Not a prepared migration")
    staged, target = Path(info["staged"]), Path(info["target"])
    _no_sidecars(staged)
    _no_sidecars(target)
    if not staged.is_file() or sha256_file(staged) != info["new_sha256"]:
        raise MigrationBlocked("Staged SQLite snapshot changed")
    old = sha256_file(target) if target.is_file() else None
    if old != info["before_sha256"]:
        raise MigrationBlocked("V2 target changed after preparation")
    if info["previous"] and sha256_file(Path(info["previous"])) != info["previous_sha256"]:
        raise MigrationBlocked("Prior V2 rollback snapshot changed")
    info["status"] = "ACTIVATING"
    _write_journal(path, info)
    os.replace(staged, target)  # staged & live share filesystem: atomic promotion
    if sha256_file(target) != info["new_sha256"]:
        raise MigrationBlocked("Promotion checksum mismatch: block V2 startup")
    info["status"] = "ACTIVE"
    _write_journal(path, info)


def migration_state(journal: Path) -> str:
    """Interrupted states are BLOCKED until user-reviewed recovery."""
    info = _load(Path(journal))
    target = Path(info["target"])
    current = sha256_file(target) if target.is_file() else None
    if info["status"] == "ACTIVATING":
        if current == info["new_sha256"]:
            return "INTERRUPTED_AFTER_PROMOTION_BLOCKED"
        if current == info["before_sha256"] and Path(info["staged"]).is_file():
            return "INTERRUPTED_BEFORE_PROMOTION_BLOCKED"
        return "UNEXPECTED_CHANGE_BLOCKED"
    if info["status"] == "ROLLING_BACK":
        return "INTERRUPTED_ROLLBACK_BLOCKED"
    if info["status"] == "ACTIVE" and current != info["new_sha256"]:
        return "ACTIVE_DB_CHANGED_NO_AUTO_ROLLBACK"
    return info["status"]


def rollback_migration(journal: Path, *, user_approved: bool = False) -> Path:
    """Preserve migrated DB as quarantine, restore previous V2 if it existed."""
    if not user_approved:
        raise MigrationBlocked("Explicit user consent needed for rollback")
    path = Path(journal)
    info = _load(path)
    if info["status"] not in ("ACTIVE", "ACTIVATING"):
        raise MigrationBlocked("Migration is not activated")
    target = Path(info["target"])
    _no_sidecars(target)
    if not target.is_file() or sha256_file(target) != info["new_sha256"]:
        raise MigrationBlocked("V2 has changed; manual reconciliation required")
    quarantined = target.with_name(target.name + ".c008_quarantine_" + info["id"])
    if quarantined.exists():
        raise MigrationBlocked("Quarantine destination already exists")
    restore = target.with_name(target.name + ".c008_restore_" + info["id"])
    if restore.exists():
        raise MigrationBlocked("Rollback staging destination already exists")
    if info["previous"]:
        previous = Path(info["previous"])
        if sha256_file(previous) != info["previous_sha256"]:
            raise MigrationBlocked("Previous V2 backup checksum mismatch")
        shutil.copyfile(previous, restore)
        if sha256_file(restore) != info["previous_sha256"]:
            raise MigrationBlocked("Restore staging checksum mismatch")
    info["status"] = "ROLLING_BACK"
    info["quarantined"] = str(quarantined)
    _write_journal(path, info)  # interrupted rollback must block app startup
    os.replace(target, quarantined)
    if restore.exists():
        os.replace(restore, target)
    info["status"] = "ROLLED_BACK"
    info["quarantined"] = str(quarantined)
    _write_journal(path, info)
    return quarantined
