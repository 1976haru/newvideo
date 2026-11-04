# Roadmap and evidence gates

Progress is tracked only as verified deliverables, not a subjective overall success claim.

| Stage | Weight | Gate |
|---|---:|---|
| R0 research/repo instructions | 10% | source docs + screenshots explained + GitHub branch + CI |
| R1 search+long adapter | 20% | mock/provider tests: >=180s truly original, missing duration rejected, 4K verified, Pexels not advertised as long |
| R2 previews | 20% | thumbnails render on Windows; real local video play/seek/mute; network/image failure diagnostics; fallback |
| R3 rights/download/library | 20% | rights evidence, user consent, selection-only download, pause/resume, hash, dedup, safe file paths |
| R4 composer/export | 20% | 3/10/30/60-min render, unique clip boundaries, codec normalization, ffprobe output validation |
| R5 packaging/release | 10% | Windows MSI/portable EXE build, cold install, non-ASCII path, reboot and data-preservation regression |

## Immediate Codex tasks (in this exact order)
1. Inspect legacy V1.0.2 code + screenshot issue, reproduce remote thumbnail error using fixture, add diagnostic logging and test. Confirm API key safety.
2. Implement provider capability matrix and separate Long/Short queries: 180s actual, no silent fallback; Commons/Archive video detail and commercial rights rules.
3. Build cached thumbnails + local Qt video player and Windows GUI smoke test. Only then expose download controls.
4. Implement SQLite and rights evidence + download queue.
5. Build composer and playlist/SRT integration.
6. Windows CI, signed/unsigned distribution warnings, zip checksums, cleanup.

## Release policy
Any red gate BLOCKS 'finished'; CI unit PASS is not Windows GUI PASS. Publish accurate overall % along with blockers.
