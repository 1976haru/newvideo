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
