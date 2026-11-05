"""C012 installer/update preservation gate for program-only versioned installs.

The V2 updater may ONLY create a NEW version subfolder in the separate V2
program root. Never initialize/overwrite/migrate V1 or V2 data, copy media,
access keyring, delete old versions, or touch recovery backups on update.
This is a reusable engine; no released EXE/installer is wired up yet.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
from uuid import uuid4


class UpdateBlocked(RuntimeError):
    """Preservation cannot be demonstrated; keep the old installation."""


def _resolved(path: Path) -> Path:
    return Path(path).resolve(strict=False)


def _overlaps(first: Path, second: Path) -> bool:
    a, b = _resolved(first), _resolved(second)
    return a == b or a.is_relative_to(b) or b.is_relative_to(a)


def _link_or_junction(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest().upper()


def _inventory(root: Path) -> tuple:
    """Read-only inventory of ALL protected files including DB, media and ZIP.

    A complete SHA inventory is deliberately conservative and can be slow for
    large media collections. Never follow symbolic links or NTFS junctions.
    """
    if _link_or_junction(root):
        raise UpdateBlocked("A protected root is a link; refuse update")
    if not root.exists():
        return ("MISSING",)
    if not root.is_dir():
        raise UpdateBlocked("Expected a protected directory")
    anchor = _resolved(root)
    records = []
    for child in sorted(root.rglob("*"), key=lambda p: str(p).casefold()):
        if _link_or_junction(child) or not _resolved(child).is_relative_to(anchor):
            raise UpdateBlocked("Linked or escaped content under a protected directory")
        relative = child.relative_to(root).as_posix()
        if child.is_dir():
            records.append((relative, "DIR"))
        elif child.is_file():
            records.append((relative, "FILE", _hash_file(child)))
        else:
            raise UpdateBlocked("Unexpected filesystem object under protected data")
    return tuple(records)


def _read_only_sqlite_check(path: Path, *, required_version: int | None) -> None:
    """Use URI read-only; never create a missing DB by sqlite3.connect(path)."""
    if not path.is_file() or _link_or_junction(path):
        raise UpdateBlocked("Required SQLite catalog missing or linked")
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise UpdateBlocked("SQLite sidecar exists: close applications first")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise UpdateBlocked("SQLite integrity verification failed")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise UpdateBlocked("SQLite foreign key verification failed")
        if required_version is not None:
            version = int(db.execute("PRAGMA user_version").fetchone()[0])
            if version != required_version:
                raise UpdateBlocked("V2 catalog schema is unsupported; refuse update")


@dataclass(frozen=True)
class UpdateLocations:
    v1_app: Path
    v1_data: Path
    recovery: Path
    v2_app: Path
    v2_data: Path

    def protected(self) -> dict[str, Path]:
        return {
            "V1_PROGRAM": Path(self.v1_app),
            "V1_DATA": Path(self.v1_data),
            "RECOVERY": Path(self.recovery),
            "V2_DATA": Path(self.v2_data),
        }

    def validate(self) -> None:
        program = Path(self.v2_app)
        if not program.is_absolute():
            raise UpdateBlocked("V2 program location must be absolute")
        if _link_or_junction(program):
            raise UpdateBlocked("V2 program root cannot be a link")
        for protected in self.protected().values():
            if not protected.is_absolute() or _overlaps(program, protected):
                raise UpdateBlocked("V2 program folder overlaps protected user files")
        for required in (self.v1_app, self.v1_data, self.recovery):
            if not Path(required).is_dir() or _link_or_junction(Path(required)):
                raise UpdateBlocked("Legacy or recovery root is absent/linked")


@dataclass(frozen=True)
class PreservationBaseline:
    files: dict[str, tuple]


def capture_preservation_baseline(locations: UpdateLocations) -> PreservationBaseline:
    locations.validate()
    _read_only_sqlite_check(Path(locations.v1_data) / "library.sqlite3",
                            required_version=None)
    v2_catalog = Path(locations.v2_data) / "catalog.sqlite3"
    if v2_catalog.exists() or v2_catalog.is_symlink():
        _read_only_sqlite_check(v2_catalog, required_version=1)
    if Path(locations.v2_data).exists() and not Path(locations.v2_data).is_dir():
        raise UpdateBlocked("V2 data location must be a directory or absent")

    recovery = Path(locations.recovery)
    for journal in recovery.rglob("c008_*.json"):
        if _link_or_junction(journal):
            raise UpdateBlocked("Linked migration journal")
        try:
            data = json.loads(journal.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise UpdateBlocked("Invalid C008 migration journal") from exc
        if data.get("checklist") != "C008" or data.get("status") not in (
            "ACTIVE", "ROLLED_BACK"
        ):
            raise UpdateBlocked("Incomplete/unknown DB migration blocks program update")
    return PreservationBaseline(
        {name: _inventory(root) for name, root in locations.protected().items()}
    )


def verify_preservation(locations: UpdateLocations, before: PreservationBaseline) -> None:
    after = capture_preservation_baseline(locations)
    if after.files != before.files:
        raise UpdateBlocked("Protected V1/V2 DB, media or backup changed during update")


def install_versioned_program(
    package: Path, locations: UpdateLocations, release_id: str
) -> Path:
    """Safely install a new program version, without ever overwriting an old one.

    A verified package must be supplied by a future distribution pipeline.
    This helper does not verify package signatures or automatically run at boot.
    """
    if not isinstance(release_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", release_id
    ):
        raise UpdateBlocked("Invalid release identifier")
    locations.validate()
    package = Path(package)
    if not package.is_dir() or _link_or_junction(package):
        raise UpdateBlocked("Update package missing or linked")
    if _overlaps(package, Path(locations.v2_app)):
        raise UpdateBlocked("Package must not be inside the live program tree")
    if any(_overlaps(package, root) for root in locations.protected().values()):
        raise UpdateBlocked("Package cannot overlap a user-data/recovery tree")

    # Validate all payload entries before any path is created.
    entries = sorted(package.rglob("*"), key=lambda p: str(p).casefold())
    if not entries or not any(p.is_file() for p in entries):
        raise UpdateBlocked("Empty program package")
    anchor = _resolved(package)
    seen_names: set[str] = set()
    for item in entries:
        if _link_or_junction(item) or not _resolved(item).is_relative_to(anchor):
            raise UpdateBlocked("Program archive contains a linked/escaped entry")
        relative = item.relative_to(package).as_posix().casefold()
        if relative in seen_names:
            raise UpdateBlocked("Case-colliding package paths")
        seen_names.add(relative)
        if not (item.is_dir() or item.is_file()):
            raise UpdateBlocked("Unsupported payload object")

    dest_root = Path(locations.v2_app)
    new_release = dest_root / ("release-" + release_id)
    if new_release.exists() or new_release.is_symlink():
        raise UpdateBlocked("Target release already exists; never overwrite")
    before = capture_preservation_baseline(locations)
    dest_root.mkdir(parents=True, exist_ok=True)
    staging = dest_root / (".c012-staging-" + uuid4().hex)
    staging.mkdir(exist_ok=False)
    try:
        for item in entries:
            relative = item.relative_to(package)
            destination = staging / relative
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(item, destination)
                if _hash_file(item) != _hash_file(destination):
                    raise UpdateBlocked("Copied program package checksum mismatch")
        verify_preservation(locations, before)
        if new_release.exists() or new_release.is_symlink():
            raise UpdateBlocked("Target release appeared during staging")
        os.rename(staging, new_release)  # same-volume directory promotion
        verify_preservation(locations, before)
        return new_release
    except Exception:
        # Never erase a possibly interrupted stage or existing release.
        # Manual review can remove ONLY the identified tool-owned staging dir.
        raise
