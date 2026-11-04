# Nature Video Studio V2 — nature-first footage workbench

Windows desktop project for finding **legally reusable nature footage**, prioritizing original takes **>=180 seconds**, previewing results, and curating 15-song playlist video backgrounds.

**Status:** Research and architecture baseline, NOT a runnable V2 application. The legacy V1.0.2 prototype was distributed separately and is not claimed to be production ready.

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
