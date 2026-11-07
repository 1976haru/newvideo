# C015 — AGENTS / CLAUDE / Korean project instructions audit

**C015 scope: PASS (2/2 points)**. These three existing repository instructions contain the user's key requirements, prohibitions on false completion, and reproducible acceptance/test expectations. This is a *documentation audit*, not proof that each product feature is implemented.

Verified on feature branch `feature/v2-research-rebuild`, 2026-11-06. Starting inspection head was `c90fa787b8edd950b2dfec135acb47fff1f6d666`.

## Documents inspected

- `AGENTS.md` — binding Codex instructions. Requires V1 failure/repo inspection before editing; 180s original only when verified; long vs short tabs separate; real Qt video previews, network diagnostics, license/source proof, credential protection, data-safe Windows packaging, unit/mock/integration/Windows GUI/real approved download tests, strict PASS/FAIL/SKIP and SHA/progress reporting, feature branch + Draft PR.
- `CLAUDE.md` — expressly delegates binding policy to `AGENTS.md` and `docs/PROJECT_INSTRUCTIONS_KO.md`, forbids claims of real Windows GUI/API tests without evidence; separate poster from real video playback; requires 180s and no short-video fallback; Korean reporting.
- `docs/PROJECT_INSTRUCTIONS_KO.md` — Korean contract for Windows 10/11 UI; safe D-drive fallback; 180s originals; 4K source verification; disjoint modes and truthful zero-results; Pexels/Pixabay/Commons/Archive; thumbnail diagnostics and real play/pause/seek; license and creator audit; explicit selection downloads and retry/backoff/allowlisting; SHA256 and media metadata; FFmpeg composition 70% stable / 30% walking; 3/10/20/30/60-min assembled results; 15-song 12s title-only SRT; Windows EXE, mock and real sample tests; ban on fake 100%; report branch/SHA, progress, PASS/FAIL/SKIP and open work.

## Cross-document criteria

| C015 concern | AGENTS | CLAUDE | Korean instructions | Outcome |
| --- | --- | --- | --- | --- |
| >=180s **original** not stitched substitute | explicit | explicit | explicit | PASS |
| Long Take / short composer never silently interchanged | explicit | explicit | explicit | PASS |
| Poster network error vs real Qt video player | explicit | explicit | explicit | PASS |
| Original 4K resolution / provenance / third-party rights | explicit | references binding | explicit | PASS |
| Credential and Windows user DB/media preserved | explicit | references binding | explicit | PASS |
| Unauthorized scraping/download or API bypass prohibited | explicit | references binding | explicit | PASS |
| Evidence-based progress; no invented PASS or 100% | explicit | no unproven GUI claim | explicit | PASS |
| Mock/unit/integration + Windows GUI/EXE and real approved sample | explicit | references binding | explicit | PASS |
| Feature branch, CI, Draft PR, main stable | explicit | references binding | explicit | PASS |

**Small consistency correction:** `docs/ROADMAP.md` previously listed output render targets `3/10/30/60` minutes, omitting the requested 20-minute target. Aligned R4 roadmap acceptance to `3/10/20/30/60` in commit `2ee072fb4597db2c3ec1f0967df6aa63a993502a`; no application code or configuration was changed.

## Scope and remaining risks

- The documentation passes C015, but R1 verified-original search, R2 actual poster/media playback, R3 legal download and library, R4 composer, R5 Windows packaged release remain separate implementation and UAT gates. Only the C011 minimal trial window has actual Windows user GUI evidence.
- Branch governance C014 is procedurally in place (feature/Draft PR), but GitHub `main` currently reports `protected=false` and has no active ruleset: separate administrative hardening required; C015 documentation does not itself enforce GitHub server-side protection.
- The project’s full 162-item checklist is not stored as a verified totals/weights source in this audit. Report verified completed-item count separately from weighted overall delivery progress; do not invent a weighted percentage.
- `CLAUDE.md` is intentionally compact and inherits the full contract from the other files. No duplicated, conflicting independent policy introduced.

## Audit execution

Read-only GitHub connector reads equivalent to the user's suggested:
```bash
cat AGENTS.md CLAUDE.md docs/PROJECT_INSTRUCTIONS_KO.md
```
The actual verification was performed by fetching and inspecting each branch file through the connected GitHub API, not by executing that shell command on the user's Windows system.

**Tests for C015 document-only change:** no new code test required; inspect CI workflow results separately. Existing automated test commands remain `python -m pytest -q -k migration_and_preservation` and `python -m pytest -q`. No real Windows files, API keys, or backup artifacts accessed.

**Decision:** C015 PASS 2/2 based on documented coverage and cross-reference checks. No V2 feature completion or Windows packaging claim follows from this acceptance.
