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
