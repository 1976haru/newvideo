"""C010: read-only V1 fallback readiness after a hypothetical V2 failure.

Reuses the proven C009 snapshot and read-only auditor, but NEVER claims that
V2 actually failed or that a user performed GUI UAT. Does not start/stop apps,
read media, mutate DBs or write to Windows Credential Manager.

To run standalone on Windows, place the pinned C009 auditor in the same
directory as NVS_C009_windows.py and invoke this script through py -3.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import gettempdir
from typing import Any


def assess_fallback(baseline: dict[str, Any], current: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    """Pure evaluator. No I/O, no password values and NO V2 GUI assertions."""
    fields = (
        ("ROOT", "root"),
        ("DB_SHA256", "db_sha256"),
        ("KEY_IDENTIFIERS", "providers"),
        ("KEY_STATUS", "key_status"),
    )
    checks = tuple(
        f"{label}={'MATCH' if baseline.get(field) == current.get(field) else 'CHANGED'}"
        for label, field in fields
    )
    backup_ok = current.get("c002_sha256_ok") is True and current.get("c004_sha256_ok") is True
    checks += (f"RECOVERY_BACKUPS={'MATCH' if backup_ok else 'CHANGED'}",)
    if any(check.endswith("CHANGED") for check in checks):
        return "C010_REVIEW_LEGACY_STATE_CHANGED", checks
    if any(current.get(field) is not True for field in
           ("app_exists", "launcher_exists", "root_exists", "db_exists")):
        return "C010_REVIEW_V1_PATH_MISSING", checks
    if current.get("keyring_check") != "CHECKED_MASKED":
        return "C010_REVIEW_KEYRING_NOT_CHECKED", checks
    statuses = current.get("key_status") or {}
    if not statuses or any(status != "PRESENT" for status in statuses.values()):
        return "C010_REVIEW_LEGACY_KEYS_UNVERIFIED", checks
    return "C010_V1_FALLBACK_READINESS_PASS_ONLY", checks


def run_with_auditor(audit: Any, baseline_file: Path) -> tuple[str, tuple[str, ...], dict[str, Any]]:
    if not baseline_file.is_file():
        return "C010_BLOCKED_C009_BASELINE_NOT_FOUND", (), {}
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    if baseline.get("checklist") != "C009":
        return "C010_BLOCKED_INVALID_BASELINE", (), {}
    archive = audit.find_trusted_zip(audit.DEFAULT_ZIP_FOLDER)
    root, root_source = audit.windows_root()
    current = audit.snapshot(
        archive=archive,
        app_folder=audit.DEFAULT_V1_APP,
        c004_backup=audit.DEFAULT_C004_BACKUP,
        root=root,
        root_source=root_source,
    )
    verdict, checks = assess_fallback(baseline, current)
    return verdict, checks, current


def load_c009_script(path: Path) -> Any:
    """Load only an explicitly selected local C009 auditor; no network access."""
    if not path.is_file():
        raise FileNotFoundError("Pinned C009 auditor is required beside this script")
    spec = importlib.util.spec_from_file_location("_c010_pinned_c009", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load trusted C009 auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only C010 V1 fallback readiness check")
    parser.add_argument("--c009-script", type=Path,
                        default=Path(__file__).with_name("NVS_C009_windows.py"))
    parser.add_argument("--baseline", type=Path,
                        default=Path(gettempdir()) / "NVS_C009_V1_baseline.json")
    args = parser.parse_args(argv)
    print("===== C010 V1 FALLBACK READINESS =====")
    try:
        if sys.platform != "win32":
            print("C010_BLOCKED_WINDOWS_ONLY")
            return 2
        audit = load_c009_script(args.c009_script)
        verdict, checks, current = run_with_auditor(audit, args.baseline)
        for item in checks:
            print(item)
        if current:
            print("ROOT_SOURCE: " + current["root_source"])
            print("KEYRING_CHECK: " + current["keyring_check"])
            for name, value in sorted(current["key_status"].items()):
                print("KEY_" + name.upper() + ": " + value)
            print("SECRET_VALUES_PRINTED: False")
        print(verdict)
        print("V2_CRASH_INJECTED: False")
        print("V2_TO_V1_GUI_ROLLBACK_TEST: SKIP_NOT_RUN")
        return 0 if verdict == "C010_V1_FALLBACK_READINESS_PASS_ONLY" else 2
    except Exception as exc:
        # Never print untrusted exception strings (may contain token or path data).
        print("C010_AUDIT_ERROR")
        print("ERROR_TYPE: " + type(exc).__name__)
        print("V2_TO_V1_GUI_ROLLBACK_TEST: SKIP_NOT_RUN")
        return 1
    finally:
        print("===== C010 REPORT END =====")


if __name__ == "__main__":
    raise SystemExit(main())
