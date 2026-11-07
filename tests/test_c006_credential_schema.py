"""Tests for static-only legacy keyring identifier inspector. No keys are touched."""
import io
from contextlib import redirect_stdout
import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from tools import audit_v102_credential_schema as s


@pytest.mark.parametrize("input_source,expected", [
    ("SERVICE='NatureVideoStudio_2026'\nimport keyring\n"
     "def lookup(provider): return keyring.get_password(SERVICE, provider)", True),
    ("import keyring\n"
     "def lookup(provider): return keyring.get_password('OtherService', provider)", False),
])
def test_detects_exact_service_name(input_source, expected):
    result = s.audit(input_source)
    assert result["service_found"] is expected


def test_prints_no_secrets_when_source_has_literal_tokens():
    text = ("SERVICE='NatureVideoStudio_2026'\n"
            "SECRET='DO_NOT_PRINT_V1_API_TOKEN_123'\n"
            "import keyring\n"
            "def f(): return keyring.get_password(SERVICE, SECRET)\n")
    audit = s.audit(text)
    report = repr(audit)
    assert audit["service_found"]
    assert "DO_NOT_PRINT_V1_API_TOKEN_123" not in report
    assert "get_password(SERVICE, SECRET)" in audit["keyring_calls"]


def test_legacy_zip_static_audit_without_keyring_import_or_execution(tmp_path, monkeypatch):
    archive = tmp_path / "legacy.zip"
    source = ("SERVICE='NatureVideoStudio_2026'\n"
              "import keyring\n"
              "def get(key): return keyring.get_password(SERVICE, key)\n"
              "EMBEDDED='SHOULD_NOT_APPEAR'\n")
    with ZipFile(archive, "w") as z:
        z.writestr("NatureVideoStudio_V1_0_2/nvs/credentials.py", source)
    monkeypatch.setattr(s, "EXPECTED_ZIP_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest().upper())
    output = io.StringIO()
    with redirect_stdout(output):
        rc = s.run(tmp_path)
    assert rc == 0
    assert "C006_STATIC_AUDIT_PASS" in output.getvalue()
    assert "SECRET_VALUES_ACCESSED: False" in output.getvalue()
    assert "SHOULD_NOT_APPEAR" not in output.getvalue()


def test_zip_checksum_mismatch_rejected(tmp_path):
    with ZipFile(tmp_path / "bad.zip", "w") as z:
        z.writestr("nvs/credentials.py", "import keyring")
    with pytest.raises(RuntimeError):
        s.find_zip(tmp_path)
