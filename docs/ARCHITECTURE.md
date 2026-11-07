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

## C020 executable service boundaries — 2026-11-07

The original diagram above is the **target application**, not the claim that
those backends currently work. C020 establishes actual headless modules and
contracts, documented in [C020_MODULE_BOUNDARIES.md](C020_MODULE_BOUNDARIES.md).

- `source_adapter.py`: `SourceAdapter` (async Protocol), `SearchQuery`,
  `SearchPage`. Concrete Pexels/Pixabay/Commons/Archive adapters: **NOT YET**.
- `search_coordinator.py`: `SearchCoordinator` asynchronously isolates
  provider failures and applies the existing strict `filter_candidates`.
  Mode-incompatible providers are never invoked; no short-clip fallback.
- `preview_service.py`: `PreviewService` runs the existing poster fetcher
  via `asyncio.to_thread`. Poster display and Qt multimedia playback are
  different services. Real GUI integration: **NOT YET**.
- `rights_review.py`: `RightsReview` wraps the cautious source license
  triage. Approval/provenance persistence: **NOT YET**.
- `download_queue.py`: `DownloadQueue` Protocol and verified-selection
  `DownloadIntent`; `UnavailableDownloadQueue` is fail closed. **No
  network download functionality.**
- `catalog.py`: `Catalog` Protocol, `UnavailableCatalog` fail closed;
  the existing C008 migration is **not** a production library service.
- `composer.py`: `Composer` Protocol, `CompositionPlan` for
  3/10/20/30/60 min output, `UnavailableComposer` fail closed.
  **No FFmpeg output functionality.**

See `tests/test_c020_module_boundaries.py`: AST import/dependency restrictions,
strict long-versus-short boundaries, provider error isolation, poster worker
thread test, rights/download guards, and explicit unavailable backend tests.
Real Qt GUI/Windows media validation remains a separate R2 acceptance gate.
