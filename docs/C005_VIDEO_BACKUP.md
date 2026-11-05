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

## User Windows read-only inventory result — 2026-11-05

**Audit PASS / Backup N/A in scanned roots / C005 full scope pending user confirmation of any other footage folders.**

User executed pinned `6b75c686f3d03a955729a2899d5069e5b3b5284f` script `& $work -Mode Audit`, and reported:

```text
===== C005 VIDEO AUDIT =====
MODE: AUDIT
SOURCE_01: D:\NatureVideoStudio
SOURCE_02: D:\03 자연풍경 비디오
VIDEO_COUNT: 0
VIDEO_BYTES: 0
VIDEO_GIB: 0
BACKUP_DIR: D:\NVS_Recovery\C005_VIDEOS
C005_NO_MEDIA_FOUND_IN_SCANNED_FOLDERS
===== C005 REPORT END =====
```

Interpretation: supported video extensions in these two roots were not found. Do not infer that all user video files are absent elsewhere. There is nothing to copy or hash-compare in these two roots, so copying is not needed and backup verification is not applicable there. C004 separately recorded downloads table at 0 rows. **No video backup was created, and no global absence claim has been made.**

Before marking C005 wholly complete, confirm whether other user-managed nature video folders exist; if yes, audit them as additional explicit scan roots and perform opt-in, capacity-checked copy-only backup. If not, mark C005 `완료 (대상 없음/N/A)` with this evidence. No file deletions or moves were authorized.

## Final C005 acceptance (2026-11-05)

**C005 = PASS (backup N/A: no existing nature footage).** The user explicitly confirmed that there are **no nature video files saved in any other folders** beyond the two scanned locations.

Evidence:
- Windows PowerShell read-only audit: `VIDEO_COUNT: 0`, `VIDEO_BYTES: 0`, `C005_NO_MEDIA_FOUND_IN_SCANNED_FOLDERS`.
- Scanned roots: `D:\NatureVideoStudio` and `D:\03 자연풍경 비디오`.
- C004 checked `downloads` SQLite table: 0 rows.
- User confirmation: no additional previously downloaded nature video files elsewhere.
- SHA sample comparison and video copy backup: **N/A** because there are zero source video files; not inaccurately described as hash-checked backups.
- User files were not moved, deleted, or overwritten. The video backup directory is only a proposed target, not evidence of files copied.

Next: C006 per the user's master checklist; do not presume its exact acceptance wording without reviewing that row. Preserve the separate C002 ZIP and C004 SQLite backups.
