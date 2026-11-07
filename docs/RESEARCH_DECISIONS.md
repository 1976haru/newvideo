# Research and technology decisions (2026-11-05)

## User screenshot and V1.0.2 source audit
- V1.0.2 screenshot: Pexels 4K results mainly 00:10 to 01:34, no 3-minute originals; poster area says preview error.
- Checked legacy ZIP's nvs/gui.py and nvs/providers.py.
- GUI only uses QNetworkAccessManager -> QLabel/QPixmap for a remote still image; no QMediaPlayer video playback at all. This is not a functioning video preview. Failed request reveals no status details.
- Pexels titles were constructed as `query · Pexels #id` because API has no human title field. Treat it as synthetic display name.
- Old duration choices all / 1min / 5min / 10-30min, missing user preferred 3min. Pexels upload policy caps at 2 minutes.
- Internet Archive query initially returned council meetings named Lake; V1.0.2 narrowed relevance via basic text regex only. Visual nature relevance is not proven.
- The repo initially had only README.md; there was no version-controlled V1 code.

## Source capabilities and constraints
Pexels API docs: https://www.pexels.com/api/documentation/
Pexels current upload limits: https://help.pexels.com/hc/en-us/articles/360042795133-What-are-the-requirements-for-uploading-videos
Pixabay video API: https://pixabay.com/api/docs/
Commons MediaWiki media API: https://www.mediawiki.org/wiki/Extension:TimedMediaHandler/API
Commons machine readable rights: https://commons.wikimedia.org/wiki/Commons:Machine-readable_data
Archive Metadata API: https://archive.org/metadata/
Archive metadata license guidance: https://internetarchive.readthedocs.io/en/stable/metadata.html
Qt Multimedia Windows FFmpeg backend: https://doc.qt.io/qt-6/qtmultimedia-index.html
FFmpeg concat guidance: https://ffmpeg.org/faq.html
YouTube reused content policy: https://support.google.com/youtube/answer/1311392?hl=en

## Relevant independent open source (INSPIRATION ONLY)
- https://github.com/xcslys99/FootageFlow (MIT): multiple source adapters, paginated research, source rights, project workspace, dedup/near-duplicates, download queue. Do not copy a large multi-source surface as V1.
- https://github.com/aivrar/mediabuddy (MIT): Windows GUI, video poster/preview, SQLite WAL, tags, local inspection, packaging. Its AI model is overkill for early V2.
- https://github.com/Breakthrough/PySceneDetect (BSD-3-Clause): actual scene detection for later composition.
- https://github.com/FFmpeg/FFmpeg (LGPL/GPL build-dependent): ffprobe metadata and video composition. Check distribution/license of bundled binaries.

## Decisions
1. Windows Python + PySide6/QtMultimedia remains practical for existing user environment and fast Python testing. Tauri 2 merits re-evaluation only if packaging size or Qt backend breaks sustained releases.
2. Stable core model + provider plugins, not a giant GUI/network module.
3. Wikimedia Commons and vetted Archive for long takes, Pexels/Pixabay for short clips. Do not promise guaranteed count of 3-minute 4K files.
4. Explicit 'original length' versus 'assembled output length', never mix.
5. License evidence per asset; never infer rights solely from availability or Creative Commons site tags.
6. Offline unit/provider tests first, Windows app/E2E and packaging release gate later.

## C013 — R0 V1.0.2 source and preview-failure audit acceptance

**Checklist status: PASS (2/2 planning/audit points).** The original November 5 V1.0.2 ZIP and `02.JPG` were audited before this verification; findings are summarized above. This acceptance covers **documented source/screenshot analysis only**, not a claim that the V1 preview fault was dynamically reproduced today or that the V2 preview has been repaired.

| Required problem | Existing source/screenshot evidence | What is established | What is *not* established |
| --- | --- | --- | --- |
| QPixmap poster request failure | `nvs/gui.py`: `QNetworkAccessManager` → image display through `QLabel/QPixmap`; `02.JPG` showed a preview-error region | The legacy remote image path lacks differentiated HTTP/network/image-failure diagnostics | Exact HTTP code, codec, TLS, CORS or timeout root cause; needs response-level logging and controlled fixtures |
| Actual video player missing | Legacy `nvs/gui.py` structure does not provide Qt Multimedia `QMediaPlayer` playback | Thumbnail rendering is **not video preview**: video play/pause/seek is not implemented in V1 | Whether a future Qt backend can play every source codec; verify with real Windows local-media tests |
| Verified original ≥180s filter missing | `nvs/gui.py` existing length choices: all / 1 minute / 5 minutes / 10–30 minutes; `nvs/providers.py` provider source audit | No dedicated verified-original-180s selection path is evidenced. An arbitrary length setting must not be advertised as verifying original duration | Actual returned durations of future providers; verify metadata and final file through independent ffprobe, and never silently substitute short clips |

**R1/R2 follow-up acceptance gates:** enforce >=180 seconds only after authentic original-duration verification; unknown duration fails the Long Take filter; keep Long Take and short-clip composition separate. For image failures, classify HTTP 403/404, TLS, timeout and decode failures with retry and original link. Add a real QMediaPlayer play/pause/seek widget and Windows smoke tests. These features remain **unimplemented** at C013 completion.

**Audit provenance boundary:** Detailed original `nvs/gui.py` and `nvs/providers.py` source is preserved in the C002 V1.0.2 ZIP, not in this V2 GitHub branch. This section reconfirms the existing recorded audit; it does not claim a fresh end-to-end test or secretly load user's private original ZIP.
