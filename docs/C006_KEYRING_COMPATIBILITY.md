# C006 — Legacy API-key compatibility plan (design acceptance)

**Scope:** Plan to reuse existing V1.0.2 Windows Credential Manager secrets without making user enter them again. This checklist line is a **planning milestone**, not a claim that V2 GUI already reads secrets.

## Evidence and limitations

- V1.0.2 archive was preserved in C002 with SHA256 `9F83FC2597E7F0DACE851EF4EF6A07956C0016D4AC99F1970ACF789C824076AE`.
- Previous V1 `nvs/credentials.py` audit identified service `NatureVideoStudio_2026`, via Python `keyring`. The **exact legacy account-name derivation** must be confirmed from preserved archive; don't guess usernames.
- V2 currently has architecture and tests but **no integrated GUI credential storage/retrieval implementation**.
- V1 existing key presence in a specific Windows user's Credential Manager is **not proven** by code inspection. Do not read, print, copy, export, or upload actual keys for this planning check.

## Compatibility decisions

1. **Same Windows account and Credential Manager backend:** V2 reads using the exact legacy `NatureVideoStudio_2026` service and discovered provider/account names, via `keyring.get_password`. Do not rename the old service or assume different Windows accounts share secrets.
2. **Read-through, not migration-by-copy:** On first provider use, prefer V2's explicitly chosen key (if one has been deliberately set). If missing, look up the existing legacy identifier. If present, use it for authorized API requests *in memory only*, without rewriting or deleting V1 credentials. Never overwrite nonempty V1 keys, and never log secret value or Authorization header.
3. **No silent defaults or fake success:** If credential is absent, user explicitly chooses whether to add a key or skip that provider. If keyring access throws/blocks, show `보안 저장소 접근 오류` with retry, not `키 없음`.
4. **Do not mutate on read or app upgrades:** No bulk `set_password` on startup, no `delete_password` in update/uninstall/reinstall. Only explicit user action can change credential entries.
5. **Provider scoping:** Use legacy identifiers only for the matching supported API provider. Keep credential material out of SQLite, settings files, crash reports, telemetry, CI fixtures and source control.
6. **Win10/11 validation gate:** On the actual original Windows account, install V2 side-by-side, launch V1 before and after V2, verify masked key status and one permitted API operation. Test missing-key, wrong Windows user, and keyring backend errors. Tests may indicate `configured/not configured` status but must never print actual key, token substring or export vault records.
7. **Rollback:** If V2 lookup fails, V1 remains runnable with its original service and existing credentials; do not reset either product's keyring entries.
8. **Packaging:** Same Python keyring backend/Windows Credential Manager support must be included in EXE deployment, without asking users to install Python.

## How to confirm V1 key names without accessing secrets

Run `tools/audit_v102_credential_schema.py` on the backup folder `D:\NVS_Recovery\C002_V1.0.2`. It validates the ZIP SHA256, parses `nvs/credentials.py` *as text only*, and prints safe service/keyring argument patterns. It **never imports keyring**, never calls `get_password`, and never reads registry credential values. Source may use a variable provider name rather than literal usernames, requiring review of call sites before marking exact mapping confirmed.

**C006 acceptance:** static service and username derivation audited + compatibility design documented (2/2 planning points). Runtime no-reentry test is a separate release gate, not evidence to award under C006 until it actually runs.
