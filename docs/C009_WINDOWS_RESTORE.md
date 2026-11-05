# C009 - Windows restoration audit (masked evidence)

**Status: IN PROGRESS, not final PASS.** C009 needs actual Windows GUI proof that key and storage settings survive, without key leakage. V2 GUI is not yet implemented, so the real V1 -> V2 no-reentry test remains blocked.

## Existing user evidence
- C002 V1 ZIP SHA256: 9F83FC2597E7F0DACE851EF4EF6A07956C0016D4AC99F1970ACF789C824076AE
- C004 V1 SQLite backup SHA256: 4D2BDC3567A6FA7CFA1577DCB42D3A582551B5F972AA55057BEB0EA7654E7973
- Legacy data root: D:\NatureVideoStudio. V1 program: D:\03 자연풍경 비디오\NatureVideoStudio_V1_0_2
- Keyring service: NatureVideoStudio_2026; account name passed as provider in V1 credentials.py.
- Planned separate V2 app/data: D:\NVS_V2_Trial_App and D:\NatureVideoStudio_V2_Data.

## Windows evidence collection
1. Close V1 and do not edit keys/settings. Download tools/audit_c009_windows.py from a pinned, reviewed GitHub commit. Run: py -3 <script> before
2. Script verifies original ZIP hash and C004 backup hash. It statically parses the known V1 source ZIP for explicit read_key/save_key literal accounts matching pexels/pixabay. If names are dynamic/unresolved it does NOT guess or enumerate vault records.
3. Read-only QSettings registry lookup; live library.sqlite3 SHA256 and backup checks. No SQLite writes or migrations.
4. When the diagnostic interpreter has keyring, calls keyring.get_password(service, exact_account) to check presence. It **does briefly access the secret in process memory** but stores/prints ONLY PRESENT/ABSENT/ACCESS_ERROR, never a real/partial key or raw exception message. If keyring is absent, it reports KEYRING_PYTHON_MODULE_MISSING, not 'no API key'.
5. A metadata-only baseline JSON goes to the user's temporary folder as NVS_C009_V1_baseline.json, with no secret values. It refuses to overwrite a prior baseline; use --baseline with a new path for reruns.
6. Open the original V1 GUI from the existing launcher. Check masked key display and original save folder; do not press Save/Delete or download anything. Capture a screenshot with private content masked, close V1.
7. Run: py -3 <script> after. It compares root path, live DB SHA256, provider identifiers, masked presence states, and backup integrity. Share ONLY console output and a redacted GUI screenshot. Do not upload the DB/ZIP/baseline/keys.

## Verdict rules
- A C009_V1_RESTORE_BASELINE_PASS means only that V1 evidence was stable before/after; it DOES NOT demonstrate a V2 GUI exists or successfully reused the key. The audit does not control GUI startup.
- **Full C009 (3/3) requires runnable V2 trial GUI**, no-reentry provider operation, original V1 data/credentials still retained, before/after path and DB validation, and masked log audit. This is blocked until C007 dual-EXE acceptance.
- If the provider names cannot be inferred from static V1 callsites, or keyring is absent, report REVIEW/SKIP and investigate without resetting secrets.
- No user files may be moved, deleted, overwritten, reset or copied for this audit. Source versioned backups remain untouched.

## Automated checks
- python -m pytest -q tests/test_c009_restore_audit.py
- python -m pytest -q

Only mock secrets and synthetic fixtures are used in CI. This is not a real Windows GUI run.
