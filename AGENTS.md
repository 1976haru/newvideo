# Codex project instructions — Nature Video Studio V2

READ docs/PROJECT_INSTRUCTIONS_KO.md, docs/ARCHITECTURE.md, docs/ROADMAP.md and docs/ACCEPTANCE.md BEFORE editing. Source of truth: user goal = free high-resolution legally usable lake/mountain/forest/nature footage for music playlist videos on Windows.

## Non-negotiable
- Before coding inspect the full repository tree, main branch, history, current tests, provider API docs and user-visible failure reports. Treat V1.0.2 as a flawed reference, not authoritative.
- Fix foundational bugs, do not merely mask or silently change filters. No invented search counts, run times, license guarantees, or QA results.
- Default Long Take preference = 180 seconds; distinguish **verified original duration** from **assembled duration**. Three-minute clips are rare on Pexels; its current upload maximum is two minutes. Never label a stitched clip as one 3-minute original.
- Support Long Take and Clip Composer in separate UI tabs. No fallback from >=180s to 15s without explicit user choice.
- Preview MUST show local/remote poster with cache, real playback when permitted/technically available, and meaningful HTTP/network/codec error. Build a fallback that opens the official source page.
- Preserve source ID, original URL, creator, URL of license, license text/version, evidence timestamp, observed duration/resolution, file hash, and download permission decision. License REVIEW is not APPROVED.
- No download unless user explicitly selects, supported URL is allowlisted and rights policy allows the requested action; block unknown/NC/ND/incompatible license by default and require human review where necessary. Do not claim guaranteed safety.
- Obey Pexels/Pixabay rules, cache TTL and request quotas; no unauthorized scraping, token theft, account bypass or bulk harvesting. No unrestricted URL fetch/SSRF.
- Never commit API credentials, user paths/data, downloaded media or secrets. Windows secrets in OS credential store; redact errors.
- Windows paths may contain Hangul; use UTF-8 Python code and ASCII/CRLF .cmd scripts. Preserve data upgrades, fail safely if D: absent or space low.
- Test unit, provider fixture, integration, Windows GUI smoke, packaging, and actual small approved download with provenance; don't claim GUI PASS based on only unit tests.
- Use feature branch + PR; do not force push main; protect existing user data and main.
- In any response report: branch/SHA, overall progress (evidence-based), changes, PASS/FAIL/SKIP with exact command, unresolved issues, next actions. A failing gate means no release.

## Workflow
1. Baseline audit + short plan.
2. Implement smallest testable unit with fixture and user-facing message.
3. Run tests before commit; CI test on Windows; fix failures.
4. Open/update draft PR; keep scope narrow and list remaining gates.
5. Only mark ready to release after Windows test and provenance sample pass.

## Priority order
P0 long duration semantics + provider capabilities + screenshot preview bug; P1 real player/cache/diagnostics; P2 long-source adapters + license evidence; P3 robust download/library; P4 composition/duplicate controls; P5 one-click package.
