# C007 — V1/V2 parallel install and isolated data layout

**Status (2026-11-06): design/code completed, automated path guards tested; **Windows dual-GUI launch NOT YET POSSIBLE** because V2 still has no integrated runnable GUI/EXE. C007 actual end-to-end gate remains SKIP/PENDING.

## Approved C007 trial paths for user's verified D: system

| Asset | Location | Protection |
| --- | --- | --- |
| Existing V1.0.2 program | `D:\03 자연풍경 비디오\NatureVideoStudio_V1_0_2` | Never overwrite or auto-update |
| Existing V1 data | `D:\NatureVideoStudio` | **Never write from V2** |
| Recovery ZIP and DB | `D:\NVS_Recovery` | Never overwrite, migrate or delete |
| New V2 trial program | `D:\NVS_V2_Trial_App` | Program binaries only |
| New V2 user data | `D:\NatureVideoStudio_V2_Data` | Catalog, cache, downloads, projects only |
| V2 catalog | `D:\NatureVideoStudio_V2_Data\catalog.sqlite3` | Separate from V1 `library.sqlite3` |

These are **planned** V2 locations, not proof that the app/executable or folders are already installed. User file storage and program distribution should **not** share a parent folder that an uninstall script could recursively delete.

For no D: (fresh PC): program `%LOCALAPPDATA%\Programs\NVS_V2_Trial_App`, V2 data `%USERPROFILE%\Videos\NatureVideoStudio_V2_Data`. The legacy V1 data fallback remains as V1 source specified and is never assumed to contain actual downloads.

## Safety invariants

1. `StorageLayout.validate()` rejects same/nested destinations using normalized Windows paths, case insensitivity, and on Windows, real paths resolved through existing junctions/reparse points.
2. V2 app and V2 data must be disjoint from each other and from V1 app, V1 data and `NVS_Recovery`.
3. The trial layout constructor **does not create, copy, migrate, move, or delete any folder**. In future, V2 startup must validate before writing; avoid write-defaulting to `D:\NatureVideoStudio` if V2 config is blank or malformed.
4. All new V2 catalog writes belong to V2 data; its media belongs under the V2 data `downloads` subtree. The only permitted V1 catalog access is explicit **read-only** SQLite URI `mode=ro`, with `PRAGMA query_only=ON`, and no V1 `Library()` constructor, which could create files.
5. Both programs may read the same Windows Credential Manager service `NatureVideoStudio_2026` only through a later tested read-through adapter. V2 never writes/deletes legacy keyring keys.
6. No automatic sync/merge; user-approved migration must have independent integrity checks, conflict handling, rollback and no duplicate records.
7. Future V2 uninstaller/updater must not recursively delete `D:\NatureVideoStudio_V2_Data`, `D:\NatureVideoStudio` or `D:\NVS_Recovery`. Ensure program install folder cannot be set to a protected path.

## C007 automated tests

`python -m pytest -q tests/test_c007_storage_layout.py`

Validate defaults on D:/no-D:, non-overlap, case-insensitive collisions, V1 read-only access, no DB creation on missing file. Both Python 3.11/3.12 Windows CI and Ubuntu CI must pass. These tests do **not** prove actual V1/V2 parallel GUI execution.

## C007 manual acceptance (deferred until V2 trial GUI/EXE is available)

- Close V1 and record its program folder & `download_root`; backup C002/C004 retained.
- Install **V2 trial** in `D:\NVS_V2_Trial_App`; confirm V2 data root at `D:\NatureVideoStudio_V2_Data`, not nested under the executable folder.
- Start V1 and V2 independently, compare shown executable/data paths; exercise minimal read-only settings and V2 catalog write, confirm V1 `library.sqlite3` SHA and `D:\NatureVideoStudio` user files unchanged before/after.
- Restart both and confirm settings persist with no shared V2/V1 QSettings namespace or database/thumbnail-cache write collision.
- Repeat with D: absent and Korean folder path. The original V1 and backups must remain untouched.

**Acceptance decision:** code gate PASS after CI; complete C007 / 2 of 2 points only after the real dual-launch + storage nonmutation evidence. Don't present planned path as installed.
