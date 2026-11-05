# C005 — Existing video file protection and lossless copy audit

Status: Code implemented; user's Windows video inventory and backup are **not yet verified**.

- Known location from C003: `D:\NatureVideoStudio` — at that time `downloads` folder absent.
- C004: `library.sqlite3` table `downloads` contains **zero rows**, **not proof of no video files**.
- Also scan the user's program workspace `D:\03 자연풍경 비디오` for media files.
- Default is **Audit**: read-only enumeration of common video extensions in exactly these two roots, count, aggregate bytes, up to 3 SHA256 samples, no new file, no manifest, no modification.
- **Backup** is opt-in, copy-only. It stores videos under `D:\NVS_Recovery\C005_VIDEOS\SOURCE_01/02` with original relative paths. Copy is verified with full SHA256 for each video; no overwrite. Existing different files block with explicit error. Requires free disk > missing bytes + 5 GiB.
- The backup is on the same D: drive; it protects against accidental app change **not physical D: drive failure**. For resilience, make an additional backup on a different disk after verifying available space.
- If the audit prints `C005_NO_MEDIA_FOUND_IN_SCANNED_FOLDERS`, do **not** assume none exist in other user-selected storage locations. Mark C005 pending until user confirms all folders were checked.
- The manifest contains **file names and hashes** and must not be committed. Report only aggregate results and a few hashes.
- Program files, DB, API keys, old backups, and media files are never deleted, renamed, moved, or overwritten. A temporary incomplete copy created by this tool may be cleaned up upon failure.
- The script uses Windows PowerShell 5.1 and accepts Hangul source paths; command lines must not accidentally treat ZIP archive as video.

Use after reviewing source: 
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\C005_Video_Backup.ps1 -Mode Audit
```
Once the audit is reviewed, explicit user action:
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\C005_Video_Backup.ps1 -Mode Backup
```

Tests (fixtures in temporary folders only):
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\test_c005_video_backup.ps1
```
