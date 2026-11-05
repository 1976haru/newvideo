"""C004: read-only audit and consistent SQLite backup of V1.0.2 user library.

Safe constraints:
- NEVER create/open the source in writable mode.
- Use sqlite3.Connection.backup for a consistent snapshot, not a raw file copy.
- Only read database schema and COUNT(*); never export private rows or API keys.
- Never overwrite existing backups; never modify the V1.0.2 source.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4


DEFAULT_SOURCE = Path(r"D:\NatureVideoStudio\library.sqlite3")
DEFAULT_BACKUP = Path(r"D:\NVS_Recovery\C004_DB")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest().upper()


def table_metadata(conn: sqlite3.Connection) -> list[dict]:
    result: list[dict] = []
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    for (name,) in rows:
        ident = '"' + name.replace('"', '""') + '"'
        columns = [
            {"name": item[1], "type": item[2]}
            for item in conn.execute("PRAGMA table_info(" + ident + ")").fetchall()
        ]
        count = int(conn.execute("SELECT COUNT(*) FROM " + ident).fetchone()[0])
        result.append({"table": name, "rows": count, "columns": columns})
    return result


def backup_library(source: Path, backup_folder: Path) -> dict:
    """Create a consistent backup and a machine-readable validation manifest.

    App must be closed for stable source hash and predictable migration evidence.
    In all cases only a mode=ro SQLite connection is opened against the source.
    """
    source = source.expanduser().resolve()
    backup_folder = backup_folder.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source library not found: {source}")
    if source.stat().st_size == 0:
        raise ValueError("Source database is empty; refusing to create a fake backup")
    if backup_folder == source.parent:
        raise ValueError("Backup must be in a separate folder from the original")

    before_sha = sha256_file(source)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"library_{stamp}_{uuid4().hex[:10]}"
    backup_folder.mkdir(parents=True, exist_ok=True)
    temporary = backup_folder / (name + ".pending.sqlite3")
    destination = backup_folder / (name + ".sqlite3")
    manifest_file = backup_folder / (name + ".manifest.json")

    if any(x.exists() for x in (temporary, destination, manifest_file)):
        raise FileExistsError("Refusing to overwrite an existing backup")

    source_uri = source.as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(source_uri, uri=True, timeout=10)) as original:
            original.execute("PRAGMA query_only = ON")
            # This is an online, SQLite-consistent backup even when journal mode differs.
            with closing(sqlite3.connect(temporary, timeout=10)) as copy:
                original.backup(copy, pages=128, sleep=0.1)
                check = [row[0] for row in copy.execute("PRAGMA integrity_check").fetchall()]
                if check != ["ok"]:
                    raise RuntimeError(f"Backup integrity check failed: {check[:3]}")
                tables = table_metadata(copy)
                foreign_key_issues = len(copy.execute("PRAGMA foreign_key_check").fetchall())
        if foreign_key_issues:
            raise RuntimeError(f"Backup foreign-key violations: {foreign_key_issues}")
        after_sha = sha256_file(source)
        if before_sha != after_sha:
            raise RuntimeError(
                "Source changed during audit; close V1.0.2 and retry. "
                "No source file was changed by this script."
            )
        os.replace(temporary, destination)
        backup_sha = sha256_file(destination)
        manifest = {
            "checklist": "C004",
            "status": "PASS",
            "source": str(source),
            "source_sha256_before": before_sha,
            "source_sha256_after": after_sha,
            "source_bytes": source.stat().st_size,
            "backup": str(destination),
            "backup_sha256": backup_sha,
            "backup_bytes": destination.stat().st_size,
            "integrity_check": "ok",
            "foreign_key_violations": foreign_key_issues,
            "tables": tables,
            "verified_at_local": datetime.now().isoformat(timespec="seconds"),
            "notes": "SQLite online backup; source opened mode=ro; no user rows exported.",
        }
        tmp_manifest = backup_folder / (name + ".manifest.pending")
        with tmp_manifest.open("w", encoding="utf-8") as output:
            json.dump(manifest, output, ensure_ascii=False, indent=2)
        os.replace(tmp_manifest, manifest_file)
        manifest["manifest_path"] = str(manifest_file)
        return manifest
    finally:
        # Only our unique incomplete backup is removed, never the source or older backups.
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C004 read-only SQLite backup + count/integrity")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--backup-folder", default=str(DEFAULT_BACKUP))
    args = parser.parse_args(argv)
    try:
        m = backup_library(Path(args.source), Path(args.backup_folder))
    except Exception as exc:
        print("C004_BACKUP_FAIL")
        print(f"REASON: {exc}")
        return 1

    print("C004_BACKUP_PASS")
    print("SOURCE: " + m["source"])
    print("SOURCE_BYTES: " + str(m["source_bytes"]))
    print("SOURCE_SHA256: " + m["source_sha256_before"])
    print("BACKUP: " + m["backup"])
    print("BACKUP_SHA256: " + m["backup_sha256"])
    print("INTEGRITY_CHECK: " + m["integrity_check"])
    print("TABLE_COUNT: " + str(len(m["tables"])))
    for entry in m["tables"]:
        cols = ",".join(x["name"] for x in entry["columns"])
        print(f"TABLE: {entry['table']} ROWS={entry['rows']} COLUMNS={cols}")
    print("MANIFEST: " + m["manifest_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
