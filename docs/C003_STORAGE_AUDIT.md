# C003 — V1.0.2 download root and library location audit

Status: **CODE PASS / WINDOWS RUNTIME PENDING** (2026-11-05). No user files changed.

## Examined immutable source
User's recovered V1.0.2 ZIP SHA256: `9F83FC2597E7F0DACE851EF4EF6A07956C0016D4AC99F1970ACF789C824076AE`; 28 archive entries. This exact hash was independently verified against the available archived V1.0.2 source.

## Source-derived findings
- `nvs/gui.py:87-89`: `QSettings('NatureVideoStudio','NatureVideoStudio')`; `self.root = Path(str(self.settings.value('download_root',str(default_root()))))`; `self.library=Library(self.root)`.
- `nvs/core.py:157-161`: If Windows D: exists, default `D:/NatureVideoStudio`. Otherwise choose `%USERPROFILE%/Videos/NatureVideoStudio` if Videos exists or `%USERPROFILE%/NatureVideoStudio`.
- `nvs/storage.py:9-14`: SQLite DB `<root>/library.sqlite3`. **Library initializer creates directory and DB**, so never instantiate Library merely to perform a read-only audit.
- `nvs/gui.py:442-453`: Changing selected folder persists `download_root` and **constructs a new Library** in the new root without migrating old DB. Audit both old and new locations before migration.
- `nvs/download.py:49-51`: Media files saved at `<root>/downloads/<category>/<source>_<id>_<title>.<ext>`.
- `nvs/gui.py:90`: Provider cache at `<root>/cache`.
- `nvs/credentials.py:3-21`: API keys use keyring service `NatureVideoStudio_2026`; do not print keys or query them during C003.
- Windows native Qt QSettings usually uses `HKCU:\\Software\\NatureVideoStudio\\NatureVideoStudio` value `download_root`, but the user's **actual** settings must be checked on their Windows PC before a PASS claim.

## PASS gate for C003
On user's Windows computer, use **read-only** registry and file metadata reads to collect:
1. configured download_root or explicit 'not stored' status;
2. resolved root folder and whether it exists;
3. `<root>\\library.sqlite3` presence and byte size (plus -wal/-shm presence);
4. `<root>\\downloads` path, file count and total bytes;
5. root `cache` path and total bytes;
6. free space on volume containing root.
Avoid printing secrets, download filenames, video metadata or any personally identifying file contents. Record **C003 PASS** only after runtime evidence. No user DB or downloads are moved/copied/deleted during C003.

## Current result (2026-11-05; user-supplied Windows read-only output)
**C003 PASS for default-root path and size inventory; actual registry value absent.**
- `SETTING_SOURCE=DEFAULT_CANDIDATE`: no explicit `download_root` was returned from the inspected HKCU key. The fallback resolved to `D:\\NatureVideoStudio`, consistent with the GUI screenshot, but **not a saved QSettings value**.
- Root exists.
- `downloads` folder absent; this is **not evidence that stored footage was deleted** and does not prove there are no videos in alternate locations.
- `cache`: 17 files, reported 0.001 GiB (rounding; approximately 1 MiB).
- `library.sqlite3` exists, 12,288 bytes (12 KiB); SQLite row count/content not inspected in C003.
- `library.sqlite3-wal` and `library.sqlite3-shm` absent at observation time.
- Disk free at observation: 50.12 GiB.
- No backup, content read, download, deletion, mutation or migration was performed by C003.
- **C004 next**: use a SQLite-consistent backup and read-only inspection, record schema and row counts; verify checksum of backup (do not copy a live SQLite database while it is being modified). Do not confuse absence of WAL with proof of DB integrity.

Do not infer media count from missing downloads folder or infer empty catalog from DB size. The user must provide C004 runtime evidence before that item can be approved.
