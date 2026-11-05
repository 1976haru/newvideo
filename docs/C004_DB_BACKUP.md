# C004 — Read-only library backup

Before running: **close Nature Video Studio V1.0.2**. This prevents concurrent source writes and yields stable SHA256 audit evidence.

Recommended Windows command after downloading `tools/audit_v102_db.py` from this trusted repository:
```powershell
py -3 .\tools\audit_v102_db.py
```

Defaults:
- read-only source: `D:\NatureVideoStudio\library.sqlite3`
- backup destination: `D:\NVS_Recovery\C004_DB`
- unique timestamped `.sqlite3` snapshot + metadata-only `.manifest.json`

Do **not** compare binary SHA of source and SQLite backup for equality: SQLite online backup can produce different database bytes. Instead ensure source SHA unchanged before vs after, validate snapshot `PRAGMA integrity_check`, inspect tables and row counts, and record backup SHA for future verification. The backup contains the full user database and must be kept private; only the console report (table names/counts and hashes, no rows) should be shared.

This utility never writes to original source DB; a separate backup path is mandatory. `C004_BACKUP_PASS` is the acceptance marker for this step.

## C004 Windows verification evidence — 2026-11-05

**Checklist verdict: PASS** based on user-provided PowerShell output from the real Windows PC.

- Invoked downloaded, pinned `9a057f5b209d92bbc9e0746fbfd8e35de48c3219` script with `py -3 "$work\audit_v102_db.py"`.
- `C004_BACKUP_PASS`, `INTEGRITY_CHECK: ok`, and `TABLE_COUNT: 1`.
- Source: `D:\NatureVideoStudio\library.sqlite3`, 12,288 bytes.
- Source SHA256: `4D2BDC3567A6FA7CFA1577DCB42D3A582551B5F972AA55057BEB0EA7654E7973`.
- Backup: `D:\NVS_Recovery\C004_DB\library_20261105_204723_1c7b3821dc.sqlite3`.
- Backup SHA256: `4D2BDC3567A6FA7CFA1577DCB42D3A582551B5F972AA55057BEB0EA7654E7973`.
- Manifest: `D:\NVS_Recovery\C004_DB\library_20261105_204723_1c7b3821dc.manifest.json`.
- Table `downloads` has **0 rows**, with columns: `item_key,source,source_id,title,creator,page_url,license_url,license_status,license_note,width,height,duration,category,tags_json,filepath,sha256,downloaded_at,probe_json`.

Note: There are **zero records in this particular SQLite downloads table**, not proof that the user has zero video files in other folders. The script performed source read-only SQLite snapshot and verified original hash before/after; the matching source/backup hash is additional evidence, not an universal requirement for SQLite snapshots. The real backup restoration and multimedia application smoke test remain separate follow-up checks. Database snapshot is private and should not be committed.

Evidence origin: user-posted output; not an interactive run by ChatGPT on the user's Windows system. No code change needed for PASS.
