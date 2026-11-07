# Nature Video Studio V2 — nature-first footage workbench

Windows desktop project for finding **legally reusable nature footage**, prioritizing original takes **>=180 seconds**, previewing results, and curating 15-song playlist video backgrounds.

**Status (2026-11-07):** The existing V2 trial GUI includes **real user-clicked Wikimedia Commons long-video and Pixabay video API search**, separate long/short filters, per-result rights/source details and asynchronous poster retrieval. Pixabay requires an API key; missing credentials or provider errors are visible rather than fabricated zero hits. Real footage file-duration/4K ffprobe, video playback, downloads, editing and release Windows EXE are **NOT implemented/NOT TESTED**. Automated mock API/Qt tests are not proof of actual provider results on the user's PC. V1.0.2 and user data remain separate.

## Principles
1. Never imply that a <3-minute stock video is an original 3-minute take.
2. Two discovery modes: **Long Take (>=180 s verified)** and **Clip Composer (short stock clips)**. Long Take does not silently relax its constraints.
3. License status is an evidence workflow, not a guarantee of copyright clearance.
4. Search, preview, download, catalog, and composition are independent modules.
5. A real local preview player, reliable poster cache, and diagnosable failures are required before release.
6. No rate-limit bypass, arbitrary third-party scraping, DRM bypass, or unauthorized YouTube downloads.
7. All work goes through tested pull requests and visible progress reports.

## Start here
- [Project instructions / 프로젝트 지침](docs/PROJECT_INSTRUCTIONS_KO.md)
- [Codex instructions](AGENTS.md)
- [Claude Code instructions](CLAUDE.md)
- [Research decisions](docs/RESEARCH_DECISIONS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap and release gates](docs/ROADMAP.md)
- [Acceptance criteria](docs/ACCEPTANCE.md)

## Planned architecture
Python 3.11+ · PySide6 · Qt Multimedia (QMediaPlayer) · requests/httpx · SQLite · ffprobe/FFmpeg · pytest · GitHub Actions Windows build.

No provider credentials or downloaded media are committed.

Project owner: 1976haru. This branch is the V2 design baseline, not V2 feature completion.

## R1 live-search Windows verification

The same existing V2 window now uses official source APIs on an explicit Search click. For actual GUI testing, source/rights display and honest failure handling, see [R1 real Windows search gate](docs/R1_LIVE_WINDOWS_SEARCH_GATE.md). No browsing, downloads, keyring writes or user-library mutations occur on launch.

## C011 - versioned V2 trial window

A minimal PySide6 window can be started after installing the optional GUI dependencies: `python -m nature_video_studio`. The title starts with `[V2 시험판]` and includes the current `v2.0.0.dev0` version. It does not access V1.0.2 files, credentials, database, or media. For an isolated one-time Windows install into a new `D:\NVS_V2_Trial_App\C011_Titlebar_*` folder, follow [C011 titlebar UAT](docs/C011_VERSION_TITLEBAR.md). The Windows titlebar screenshot is not yet verified.

## C024/C025 — existing V2 trial installation

Do not create a new installation folder for each checklist. The user runs the existing V2 trial at D:\\NVS_V2_Trial_App\\C011_Titlebar_10206483 and upgrades its **code only** with the tested same-install updater. For [C025 180-second original gate](docs/C025_ORIGINAL_DURATION_GATE.md), use the tested commit 106d6c08f4247e54bbbff3d1d3d7a917b4b4703c, then click the offline C025 duration rule self-check in the Long Original tab. **Offline PASS is not verified footage from a real provider.** See [single-install procedure](docs/LOCAL_V2_SINGLE_INSTALL_UPDATE.md).
