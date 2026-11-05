# C008 — V1 → V2 SQLite migration policy, schema versions, rollback

Status: implementation and synthetic fixtures committed; final PASS requires CI evidence. This is **not a live migration**; V2 GUI/EXE and user-approved migration UI do not yet exist.

## Source evidence (from C004 and user)
- V1 DB: D:\NatureVideoStudio\library.sqlite3; 12,288 bytes; SHA256 4D2BDC3567A6FA7CFA1577DCB42D3A582551B5F972AA55057BEB0EA7654E7973; downloads table contains 0 rows.
- V1 downloads fields (18): item_key, source, source_id, title, creator, page_url, license_url, license_status, license_note, width, height, duration, category, tags_json, filepath, sha256, downloaded_at, probe_json.
- Existing C004 copy: D:\NVS_Recovery\C004_DB\library_20261105_204723_1c7b3821dc.sqlite3. Keep private and unchanged.
- V2 planned separate catalog: D:\NatureVideoStudio_V2_Data\catalog.sqlite3. Never create a V2 DB at the legacy location.
- Legacy SQLite user_version 0 does not denote a V2 schema version. V2 schema begins at PRAGMA user_version=1; migrations are recorded in schema_migrations.

## Up/down version matrix

| Source | Target | Up | Down/rollback |
| --- | --- | --- | --- |
| V1 legacy 18-column downloads | V2 schema v1 | Import source read-only to staged V2 DB; keep the 18 fields in legacy_downloads and a separate assets index | V1 is NEVER changed; remove no source files |
| V2 absent | V2 v1 | Create staged catalog with PRAGMA user_version=1; activate only with user approval | Quarantine promoted catalog (non-destructive), then leave live V2 catalog absent |
| V2 v1 existing | V2 v1 plus V1 rows | SQLite-consistent clone of existing V2 to staging; snapshot original V2; import new source SHA only | On explicit rollback restore verified previous V2 snapshot; quarantine migrated catalog |
| Future V2 v1 | V2 v2+ | Require new numbered forward migration, safety fixtures and new pre-upgrade snapshot | No automatic destructive DROP/DOWN SQL; restore verified prior snapshot with user consent |
| Unknown version/schema | any | BLOCK | Keep untouched |

## Mandatory safety gates

1. Audit user V1 from an immutable, verified C004 snapshot only: open SQLite mode=ro, query_only=ON, PRAGMA integrity_check, PRAGMA foreign_key_check, exact legacy fields. Verify source SHA before/after. Never call V1 Library() or any API key accessor.
2. PREPARE: no writes to live V1 or live V2. Reject overlapping paths and active SQLite WAL/journal sidecars. Build staged DB within target's volume; preserve prior V2 using sqlite3.Connection.backup and SHA256. Use one SQLite transaction for imported rows and version metadata.
3. Historical media facts are unverified: imported V1 license_status is provenance ONLY, with V2 rights_review_status=GENERAL_REVIEW; original_duration_verified=0 and file_verified=0. Retain legacy resolution and duration metadata for later ffprobe/rights inspection, but never label them verified 4K or >=180s originals. Retain legacy filepath string as a reference, without video copying. API keys remain in Windows keyring.
4. ACTIVATE: explicitly approved only; verify staged SHA, original target SHA and rollback snapshot SHA; atomically promote stage with os.replace from the same volume; state transitions PREPARED → ACTIVATING → ACTIVE in the durable journal.
5. CRASH RECOVERY: startup blocks on incomplete ACTIVATING marker. Detect before/after promotion with hashes. Never silently reset or replace a user DB; manual user-approved recovery first.
6. ROLLBACK: requires separate explicit approval and unchanged activated target SHA. Quarantine migrated DB without deletion. Restore previously hashed V2 snapshot (if one existed) or leave target absent. If V2 was modified after activation, reject automatic rollback rather than losing user work.
7. RETRY: refuse duplicate source SHA imports and conflicting asset IDs; unresolved migration journals require handling before further migration. Errors in DB checks, disk space, I/O or schema must not be treated as success.

## Automated evidence

Test synthetic local fixtures ONLY:
  python -m pytest -q tests/test_migration.py
Full regression:
  python -m pytest -q

Tests include 0-row actual-shape V1 fixture, nonempty metadata preservation, Korean text/path support, conservative rights/duration treatment, existing V2 preservation, explicit consent, rollback, crash-after/before promotion detection, changed live DB refusal, unknown schema, corrupt/absent DB, path overlap and WAL sidecars. GitHub Actions Windows Python 3.11/3.12 and Ubuntu Python 3.11/3.12 expected; report only observed results.

## Work still required before real migration
- C007 side-by-side V2 GUI app with dedicated database lifecycle;
- exact Windows system-drive and storage layout integration and preflight disk-reserve handling;
- tests for SQLite busy, disk-full, concurrent access, journal power-loss/crash injection and Win10/11 real EXE recovery UX;
- user-visible preview of the copy plan and explicit approval before promotion;
- source C004 backup authenticity check immediately before use; final V1 DB content hash and V2 post-migration validation;
- production startup gate integration, including detection of abandoned journals.

Do not run migration against a user's real D: drive until those gates are verified and the user consents. C008 is a schema/strategy + synthetic tests milestone, not a claim that user data was transferred.
