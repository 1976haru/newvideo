"""C009 V1 Windows restoration evidence, no passwords or user data exported.

Run BEFORE and AFTER launching the unchanged V1 GUI to view its masked key
fields. Only the dedicated C009 baseline JSON is written. Existing files,
Credential Manager and the application's databases are never modified.

The keyring API necessarily retrieves a key into process memory to test whether
it exists, but its value is never serialized, logged, displayed, or transmitted.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import gettempdir
from zipfile import ZipFile

SERVICE = "NatureVideoStudio_2026"
TRUSTED_ZIP_SHA256 = "9F83FC2597E7F0DACE851EF4EF6A07956C0016D4AC99F1970ACF789C824076AE"
TRUSTED_C004_SHA256 = "4D2BDC3567A6FA7CFA1577DCB42D3A582551B5F972AA55057BEB0EA7654E7973"
SUPPORTED_ACCOUNTS = frozenset({"pexels", "pixabay"})
DEFAULT_V1_APP = Path(r"D:\03 자연풍경 비디오\NatureVideoStudio_V1_0_2")
DEFAULT_ZIP_FOLDER = Path(r"D:\NVS_Recovery\C002_V1.0.2")
DEFAULT_C004_BACKUP = Path(
    r"D:\NVS_Recovery\C004_DB\library_20261105_204723_1c7b3821dc.sqlite3"
)
DEFAULT_BASELINE = Path(gettempdir()) / "NVS_C009_V1_baseline.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def find_trusted_zip(folder: Path) -> Path:
    if not folder.is_dir():
        raise RuntimeError("C002 archive folder missing")
    matches = [p for p in folder.glob("*.zip")
               if sha256_file(p) == TRUSTED_ZIP_SHA256]
    if len(matches) != 1:
        raise RuntimeError("Exactly one verified C002 source ZIP required")
    return matches[0]


def source_account_ids(archive: Path) -> tuple[str, ...]:
    """Find only explicit Pexels/Pixabay identifiers in legacy call sites.

    Never execute V1 Python. Unknown/dynamic account names remain unresolved;
    do not guess, enumerate credential vault entries or use broad probes.
    """
    found: set[str] = set()
    with ZipFile(archive) as zip_file:
        for name in zip_file.namelist():
            if not name.endswith(".py") or "/nvs/" not in "/" + name.replace("\\", "/"):
                continue
            tree = ast.parse(zip_file.read(name).decode("utf-8-sig"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                method = (node.func.attr if isinstance(node.func, ast.Attribute)
                          else node.func.id if isinstance(node.func, ast.Name) else "")
                if method not in ("read_key", "save_key"):
                    continue
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.casefold() in SUPPORTED_ACCOUNTS:
                        found.add(arg.value)  # preserve exact Windows username case
    return tuple(sorted(found))


def windows_root() -> tuple[str, str]:
    """Windows QSettings registry read only; no GUI startup and no setting writes."""
    if sys.platform != "win32":
        raise RuntimeError("Windows-only verification tool")
    import winreg

    saved = None
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\NatureVideoStudio\NatureVideoStudio",
            0,
            winreg.KEY_READ,
        ) as key:
            value, _ = winreg.QueryValueEx(key, "download_root")
            if isinstance(value, str) and value.strip():
                saved = value
    except (OSError, FileNotFoundError):
        pass

    if saved:
        return str(Path(saved)), "QSETTINGS_SAVED"
    if Path("D:\\").exists():
        return r"D:\NatureVideoStudio", "DEFAULT_CANDIDATE"
    home = Path.home()
    videos = home / "Videos"
    root = videos / "NatureVideoStudio" if videos.is_dir() else home / "NatureVideoStudio"
    return str(root), "DEFAULT_CANDIDATE"


def key_status(account_ids: tuple[str, ...], lookup=None) -> tuple[str, dict[str, str]]:
    """No plaintext value leaves this frame. Exceptions are intentionally redacted."""
    if not account_ids:
        return "ACCOUNT_NAMES_UNRESOLVED", {}
    if lookup is None:
        try:
            import keyring
        except ImportError:
            return "KEYRING_PYTHON_MODULE_MISSING", {}
        lookup = keyring.get_password
    result = {}
    for account in account_ids:
        try:
            # Keep only a boolean. NEVER log or persist the returned secret.
            result[account] = "PRESENT" if bool(lookup(SERVICE, account)) else "ABSENT"
        except Exception:
            result[account] = "ACCESS_ERROR"
    return "CHECKED_MASKED", result


def snapshot(
    *, archive: Path, app_folder: Path, c004_backup: Path,
    root: str, root_source: str, lookup=None,
) -> dict:
    if sha256_file(archive) != TRUSTED_ZIP_SHA256:
        raise RuntimeError("C002 SHA256 mismatch; fail closed")
    if sha256_file(c004_backup) != TRUSTED_C004_SHA256:
        raise RuntimeError("C004 backup SHA256 mismatch; fail closed")
    accounts = source_account_ids(archive)
    status, keys = key_status(accounts, lookup)
    db = Path(root) / "library.sqlite3"
    return {
        "checklist": "C009",
        "app_exists": app_folder.is_dir(),
        "launcher_exists": (app_folder / "START_NATURE_VIDEO_STUDIO.cmd").is_file(),
        "root": root,
        "root_source": root_source,
        "root_exists": Path(root).is_dir(),
        "db_exists": db.is_file(),
        "db_sha256": sha256_file(db) if db.is_file() else None,
        "c002_sha256_ok": True,
        "c004_sha256_ok": True,
        "providers": list(accounts),
        "keyring_check": status,
        "key_status": keys,
    }


def assess(before: dict, after: dict) -> tuple[str, list[str]]:
    checks = (
        ("ROOT", before.get("root") == after.get("root")),
        ("DB_SHA256", before.get("db_sha256") == after.get("db_sha256")),
        ("KEY_IDENTIFIERS", before.get("providers") == after.get("providers")),
        ("KEY_STATUS", before.get("key_status") == after.get("key_status")),
        ("RECOVERY_BACKUPS", bool(after.get("c002_sha256_ok") and after.get("c004_sha256_ok"))),
    )
    outcomes = [name + "=" + ("MATCH" if ok else "CHANGED")
                for name, ok in checks]
    if any(not ok for _, ok in checks):
        return "REVIEW_CHANGED_STATE", outcomes
    if not after["app_exists"] or not after["root_exists"] or not after["db_exists"]:
        return "REVIEW_MISSING_PATH", outcomes
    if not after["key_status"] or any(x != "PRESENT" for x in after["key_status"].values()):
        return "REVIEW_KEY_UNVERIFIED", outcomes
    return "V1_RESTORE_BASELINE_PASS", outcomes


def report(data: dict) -> None:
    print("===== C009 MASKED RESTORE AUDIT =====")
    print("APP_FOLDER_EXISTS: " + str(data["app_exists"]))
    print("LAUNCHER_EXISTS: " + str(data["launcher_exists"]))
    print("ROOT_SOURCE: " + data["root_source"])
    print("ROOT: " + data["root"])
    print("ROOT_EXISTS: " + str(data["root_exists"]))
    print("DB_EXISTS: " + str(data["db_exists"]))
    print("DB_SHA256: " + (data["db_sha256"] or "NOT_FOUND"))
    print("C002_ZIP_SHA256_MATCH: " + str(data["c002_sha256_ok"]))
    print("C004_DB_BACKUP_SHA256_MATCH: " + str(data["c004_sha256_ok"]))
    print("KEYRING_CHECK: " + data["keyring_check"])
    for account, status in sorted(data["key_status"].items()):
        print("KEY_" + account.upper() + ": " + status)
    print("SECRET_VALUES_PRINTED: False")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="C009 read-only V1 restoration inventory")
    parser.add_argument("stage", choices=("before", "after"))
    parser.add_argument("--source-folder", type=Path, default=DEFAULT_ZIP_FOLDER)
    parser.add_argument("--app-folder", type=Path, default=DEFAULT_V1_APP)
    parser.add_argument("--backup-db", type=Path, default=DEFAULT_C004_BACKUP)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args(argv)
    try:
        archive = find_trusted_zip(args.source_folder)
        root, root_source = windows_root()
        data = snapshot(
            archive=archive, app_folder=args.app_folder,
            c004_backup=args.backup_db, root=root, root_source=root_source,
        )
        report(data)
        if args.stage == "before":
            # Audit artifact contains only presence flags and hashes, NO secrets.
            # Never overwrite a previous baseline without reviewing it first.
            with args.baseline.open("x", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("C009_BEFORE_BASELINE_SAVED")
        else:
            saved = json.loads(args.baseline.read_text(encoding="utf-8"))
            result, checks = assess(saved, data)
            for check in checks:
                print(check)
            print("C009_" + result)
        print("===== C009 REPORT END =====")
        return 0
    except Exception as exc:
        # Do not print arbitrary exception text, which could contain credential metadata.
        print("C009_AUDIT_ERROR")
        print("ERROR_TYPE: " + type(exc).__name__)
        print("===== C009 REPORT END =====")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
