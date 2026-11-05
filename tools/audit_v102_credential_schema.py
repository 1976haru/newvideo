"""C006: static, SECRET-FREE audit of legacy V1.0.2 credential key identifiers.

Does not execute legacy code, import keyring, or access Windows Credential Manager.
Does not print credential values, unrelated strings, or user-owned configuration.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re
import sys
from zipfile import ZipFile

EXPECTED_ZIP_SHA256 = "9F83FC2597E7F0DACE851EF4EF6A07956C0016D4AC99F1970ACF789C824076AE"
SERVICE = "NatureVideoStudio_2026"
ALLOWED_WORDS = {"pexels", "pixabay", "wikimedia", "commons", "archive",
                 "internet_archive", "naturevideostudio_2026", "api_key"}
METHODS = {"get_password", "set_password", "delete_password"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _safe_node(node: ast.AST) -> str:
    """Represent account/service expressions without reproducing unknown literals."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return repr(node.value) if node.value.lower() in ALLOWED_WORDS else "<string>"
        return "<constant>"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _safe_node(node.value) + "." + node.attr
    if isinstance(node, ast.Call):
        return "CALL(" + _safe_node(node.func) + ")"
    if isinstance(node, ast.JoinedStr):
        return "f-string(template-withheld)"
    if isinstance(node, ast.BinOp):
        return _safe_node(node.left) + " OP " + _safe_node(node.right)
    if isinstance(node, ast.Subscript):
        return _safe_node(node.value) + "[...]"
    if isinstance(node, ast.Tuple):
        return "tuple(" + ",".join(_safe_node(x) for x in node.elts) + ")"
    return type(node).__name__


def audit(source: str) -> dict:
    tree = ast.parse(source)
    service_found = False
    patterns: list[str] = []
    functions: list[str] = []
    identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value == SERVICE:
                service_found = True
            if node.value.lower() in ALLOWED_WORDS and node.value != SERVICE:
                identifiers.add(node.value.lower())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in METHODS:
            args = ", ".join(_safe_node(x) for x in node.args[:2])
            patterns.append(f"{node.func.attr}({args})")
    return {"service_found": service_found, "keyring_calls": sorted(set(patterns)),
            "key_identifiers": sorted(identifiers), "function_names": sorted(set(functions))}


def find_zip(folder: Path) -> Path:
    if not folder.is_dir():
        raise FileNotFoundError(f"Backup folder not found: {folder}")
    matching = []
    for p in folder.glob("*.zip"):
        if sha256(p) == EXPECTED_ZIP_SHA256:
            matching.append(p)
    if len(matching) != 1:
        raise RuntimeError(f"Expected precisely one V1.0.2 ZIP with recorded SHA256; found {len(matching)}")
    return matching[0]


def run(folder: Path) -> int:
    try:
        zip_path = find_zip(folder)
        with ZipFile(zip_path) as z:
            possible = [n for n in z.namelist()
                        if n.replace("\\", "/").endswith("/nvs/credentials.py")
                        or n.replace("\\", "/") == "nvs/credentials.py"]
            if len(possible) != 1:
                raise RuntimeError(f"Expected exactly one nvs/credentials.py; found {len(possible)}")
            raw = z.read(possible[0])
            text = raw.decode("utf-8-sig")
        result = audit(text)
        print("C006_STATIC_AUDIT_" + ("PASS" if result["service_found"] and result["keyring_calls"] else "REVIEW"))
        print("ZIP_SHA256_MATCH: True")
        print("SERVICE_IDENTIFIER: " + (SERVICE if result["service_found"] else "NOT_FOUND"))
        print("KEYRING_CALL_PATTERNS:")
        for x in result["keyring_calls"]:
            print("  " + x)
        print("ALLOWED_KEY_IDENTIFIERS: " + (", ".join(result["key_identifiers"]) or "(none)"))
        print("FUNCTION_NAMES: " + (", ".join(result["function_names"]) or "(none)"))
        print("SECRET_VALUES_ACCESSED: False")
        print("===== C006 STATIC AUDIT END =====")
        return 0 if result["service_found"] and result["keyring_calls"] else 2
    except (OSError, RuntimeError, SyntaxError, UnicodeDecodeError, ValueError) as exc:
        print("C006_STATIC_AUDIT_FAIL")
        print("REASON_TYPE: " + type(exc).__name__)
        print("===== C006 STATIC AUDIT END =====")
        return 1


if __name__ == "__main__":
    location = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\NVS_Recovery\C002_V1.0.2")
    raise SystemExit(run(location))
