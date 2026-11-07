"""C007: V1/V2 side-by-side storage layout policy (NO FILESYSTEM WRITES).

V2 executable files, V2 user data, V1's original app/data, and recovery files
MUST occupy disjoint directories. The policy is deliberately separate from GUI
and does not create or migrate any directory.
"""
from __future__ import annotations

from dataclasses import dataclass
import ntpath
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import sys
from urllib.parse import quote


# V1 QSettings: QSettings("NatureVideoStudio", "NatureVideoStudio").
# Never use that namespace for V2, or a V2 setting could overwrite V1 values.
V2_SETTINGS_ORGANIZATION = "NatureVideoStudioV2"
V2_SETTINGS_APPLICATION = "NatureVideoStudioV2Trial"


class UnsafeLayout(ValueError):
    """A path collides with another app or the preserved user data."""


def _windows_absolute(path: str) -> str:
    """Normalize a local, drive-absolute Windows path for overlap checks."""
    if not isinstance(path, str) or not path.strip():
        raise UnsafeLayout("Storage path is missing")
    value = ntpath.normcase(ntpath.normpath(path.strip()))
    drive, tail = ntpath.splitdrive(value)
    if not drive or not tail.startswith("\\") or drive.startswith("\\\\"):
        raise UnsafeLayout("Storage locations must be absolute local Windows paths")
    # ntpath.normpath turns 'C:\\a\\..\\b' into C:\\b; check the resolved destination.
    if drive == value.rstrip("\\"):
        raise UnsafeLayout("Drive root is unsafe as an application/storage folder")
    return value.rstrip("\\")


def _real_windows_path(path: str) -> str:
    """Follow pre-existing Windows reparse-point paths before authorizing writes."""
    canonical = _windows_absolute(path)
    if sys.platform == "win32":
        canonical = _windows_absolute(str(Path(path).resolve(strict=False)))
    return canonical


def _is_nested_or_same(one: str, two: str) -> bool:
    try:
        common = ntpath.commonpath([one, two])
    except ValueError:
        return False  # Different local drives
    return common == one or common == two


@dataclass(frozen=True)
class StorageLayout:
    v1_app: str
    v1_data: str
    recovery: str
    v2_app: str
    v2_data: str

    def validate(self) -> "StorageLayout":
        names = {
            "V1_APP": self.v1_app,
            "V1_DATA": self.v1_data,
            "RECOVERY": self.recovery,
            "V2_APP": self.v2_app,
            "V2_DATA": self.v2_data,
        }
        normalized = {name: _real_windows_path(path) for name, path in names.items()}
        protected = ("V1_APP", "V1_DATA", "RECOVERY")
        for writable in ("V2_APP", "V2_DATA"):
            for forbidden in (*protected, "V2_DATA" if writable == "V2_APP" else "V2_APP"):
                if _is_nested_or_same(normalized[writable], normalized[forbidden]):
                    raise UnsafeLayout(
                        f"{writable} overlaps {forbidden}; refusing to use the location"
                    )
        return self

    @property
    def v2_catalog(self) -> str:
        self.validate()
        return ntpath.join(self.v2_data, "catalog.sqlite3")

    @property
    def v2_media_folder(self) -> str:
        self.validate()
        return ntpath.join(self.v2_data, "downloads")

    @property
    def legacy_catalog(self) -> str:
        return ntpath.join(self.v1_data, "library.sqlite3")


def trial_layout(
    *,
    has_d_drive: bool,
    user_profile: str,
    local_app_data: str,
    legacy_app: str | None = None,
    legacy_data: str | None = None,
    videos_folder_exists: bool = True,
) -> StorageLayout:
    """Generate the V2 trial's independent app and data roots.

    For the real user's existing D: system the paths follow the verified C003
    location. Call validate() before any actual V2 filesystem creation.
    """
    if has_d_drive:
        legacy_app = legacy_app or r"D:\03 자연풍경 비디오\NatureVideoStudio_V1_0_2"
        legacy_data = legacy_data or r"D:\NatureVideoStudio"
        result = StorageLayout(
            v1_app=legacy_app,
            v1_data=legacy_data,
            recovery=r"D:\NVS_Recovery",
            v2_app=r"D:\NVS_V2_Trial_App",
            v2_data=r"D:\NatureVideoStudio_V2_Data",
        )
    else:
        v1_default = (
            ntpath.join(user_profile, "Videos", "NatureVideoStudio")
            if videos_folder_exists
            else ntpath.join(user_profile, "NatureVideoStudio")
        )
        result = StorageLayout(
            v1_app=legacy_app or ntpath.join(local_app_data, "Programs", "NatureVideoStudio_V1"),
            v1_data=legacy_data or v1_default,
            recovery=ntpath.join(user_profile, "Documents", "NVS_Recovery"),
            v2_app=ntpath.join(local_app_data, "Programs", "NVS_V2_Trial_App"),
            v2_data=ntpath.join(user_profile, "Videos", "NatureVideoStudio_V2_Data"),
        )
    return result.validate()


def inspect_legacy_download_counts(source_db: Path) -> int:
    """Optional read-only SQLite probe; never creates DB or calls V1 Library().

    Not for migration or credentials; only used if the user explicitly asks
    V2 to inspect the V1 DB. Safe if source path does not exist: fails closed.
    """
    if not source_db.is_file():
        raise FileNotFoundError("Legacy library does not exist; no DB created")
    uri = source_db.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as connection:
        connection.execute("PRAGMA query_only=ON")
        return int(connection.execute('SELECT COUNT(*) FROM "downloads"').fetchone()[0])
