# V2 architecture

UI (PySide6): tabs Long Take / Clip Composer / Library / Downloads / Settings.
  │ typed requests & signals; no blocking network calls
Application services: SearchCoordinator; PreviewService; RightsReview; DownloadQueue; LibraryCatalog; Composer.
  │
Provider interface: search(SearchQuery) -> SearchPage[MediaCandidate], resolve(id) -> MediaDetail.
  ├ PexelsShortAdapter (official API; short clips)
  ├ PixabayShortAdapter (official API; duration verify)
  ├ CommonsLongAdapter (MediaWiki API videoinfo / file rights)
  ├ ArchiveLongAdapter (Advanced Search + per item metadata/rights)
  └ UserLocalAdapter (user-owned footage)
  │
Data: SQLite WAL tables assets, renditions, rights_evidence, preview_cache, downloads, clips, projects, project_clips, exports.

Core candidate: source, source_id, source_url, creator, title, duration_seconds, duration_verified, rendition width/height/fps/format, preview_url, license metadata and risk level, relevancy signals, rank explanation.
- SearchQuery: language+place+natural-landscape concepts, min_original_duration=180, max_original_duration optional, resolution 4k_only/4k_preferred/fhd, mode long/short.
- Never coerce unknown duration into pass for long.
- Search results from one provider cannot erase others on provider error; per-source result/status.
- Preview network policy: HTTPS allowlist, redirect revalidation, timeout, MIME/content size check, cached image, user-visible error code, QMediaPlayer backend for permitted media and verified local files.
- Download policy: explicit choice + rights review, preflight expected media type/size and disk space, staged writes + hashes and atomic commit, safe pause/partial resume checks, provenance saved.
- Composer: draft edit decision list (.json), separate render queue using ffprobe and FFmpeg, codec/audio/timebase normalization, controlled loop avoidance, transitions. Preview low-res draft before 4K export.
- Secrets: Windows keyring, no keys in SQLite/readme/logs/CI artifacts.
- Packaging: pyinstaller on windows-latest with pinned deps, pyqt multimedia backend health check, zip+checksum+manifest.

### QA failure classes
QA_PREVIEW_POSTER_FETCH; QA_PREVIEW_PLAYBACK; QA_DURATION_FILTER; QA_PROVIDER_RATE_LIMIT; QA_LICENSE_EVIDENCE; QA_DOWNLOAD_INTEGRITY; QA_COMPOSER_OUTPUT; QA_WINDOWS_PACKAGING; QA_API_KEY_SECURITY. Track separately to avoid false PASS.
