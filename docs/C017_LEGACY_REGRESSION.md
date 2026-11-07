# C017 — R0 V1.0.2 preview/media and Lake-meeting regression evidence

**Status: PARTIAL — offline regression fixture corpus and CI checks are implemented, real V1.0.2 failure capture remains unverified.** Internal checkpoint credit: **2/3 provisional** (fixture cases + deterministic cross-platform pytest); final 3/3 remains blocked on real observed evidence where feasible.

## Historical facts versus synthetic sample

- Historical evidence: `docs/RESEARCH_DECISIONS.md` records V1.0.2 `02.JPG` showing generic poster preview failure, without real HTTP response status; `nvs/gui.py` used `QNetworkAccessManager` and `QLabel/QPixmap` (no `QMediaPlayer` player); `nvs/providers.py` produced Archive Lake-meeting search false positives.
- Historical source archive remains in the user's original C002 verified V1.0.2 ZIP (not in GitHub). Its SHA256 was `9F83FC2597E7F0DACE851EF4EF6A07956C0016D4AC99F1970ACF789C824076AE`.
- The current C017 fixture file `tests/fixtures/legacy_v102_failures.json` is a **new synthetic offline surrogate**. The HTTP codes, fake FFmpeg stderr strings, malformed-MP4 hex and fictional Archive-like meeting IDs are **not captured real-world errors or real item IDs**.
- Since **V1.0.2 did not have an actual video player**, a "V1 codec playback error" cannot be faithfully reproduced or attributed to V1. A new V2 real Qt codec test is the appropriate later scope. C017 only captures error-signature proxies.

## Artifact inventory

| File | Function |
| --- | --- |
| `tests/fixtures/legacy_v102_failures.json` | 12 fake HTTP/image/network/redirect scenarios, 6 FFmpeg-style playback stderr signatures, 1 tiny invalid-MP4 hex header, 4 fictional Lake title cases |
| `tests/fixtures/README_C017.md` | Full offline replay steps; provenance caveats; what can/cannot be claimed; follow-up real recording checklist |
| `tests/test_legacy_regression.py` | Parametric fixture integrity, transport/status/error code replay, codec-string classification and secret redaction, invalid file header, meeting keyword-only false positive |
| `src/nature_video_studio/playback_diagnostics.py` | Bounded stable error classification; not integrated with Qt video player and not a real codec tester |
| `.github/workflows/ci.yml` | Dedicated `python -m pytest -q tests/test_legacy_regression.py` step, in addition to existing C012 preservation gate and full suite |

## Safe replay

From an isolated checkout with Python 3.11+:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_legacy_regression.py
python -m pytest -vv tests/test_legacy_regression.py
python -m pytest -q
```

Pytest uses in-memory fake sessions and `tmp_path`; no live network calls, credentials, user files or copyrighted video assets. A test asserting the naive `lake` keyword rule is **documenting the bug pattern**, not an acceptance test that V2 correctly rejects all meetings. The existing nature-relevance gate is still unfinished.

## Minimum future acceptance evidence for 3/3

1. User-approved V1.0.2 Windows reproduction of the generic poster failure with controlled HTTP response and masked `QNetworkReply` status, no API key leakage. The prior `02.JPG` alone does not prove HTTP 403, TLS, or timeout.
2. New V2 Windows Qt playback on a locally generated known-good and intentionally invalid/unsupported video; report actual codec/backend errors and `ffprobe` evidence. Never misattribute this to V1.
3. Real authorization-safe provider response or sanitized item metadata showing a non-nature Lake meeting and expected reject/review oracle; avoid fictional items being presented as real historical results.
4. Evidence of error type exposed to users; distinguish **poster** from **video** errors. Later R1/R2 tests must prove actual nature filtering and media playback in Windows.

**C017 does not cure V1 preview or show that V2 search or Qt player is fully functional.** C013 audit and this C017 fixture corpus are separate from finished R1 and R2 acceptance.

## Test-status reporting

CI source code and exact output are recorded after the latest workflow completes. Do not claim an in-progress run is PASS. Main remains unchanged, feature branch and Draft PR #1 are preserved.

## GitHub Actions real CI evidence — 2026-11-06

Code SHA: `e88b138c71c7d2c42eaf5ee0625985704c8306e7`; [CI run 42123984605](https://github.com/1976haru/newvideo/actions/runs/42123984605).

All six jobs completed **SUCCESS**:
- Windows / Ubuntu, Python 3.11 and 3.12: PASS.
- Windows C011 Qt titlebar smoke: PASS.
- Windows C005 PowerShell nonmutation fixtures: PASS.

Windows Python 3.11 job log reports:
```text
python -m pytest -q -k migration_and_preservation
26 passed, 151 deselected

python -m pytest -q tests/test_legacy_regression.py
26 passed

python -m pytest -q
176 passed, 1 skipped
```

These numbers are for the synthetic fixture and full suite, not a fresh V1.0.2 live GUI reproduction. No actual external API/codec capture was performed. The later documentation-only commit does not change executable test logic.
