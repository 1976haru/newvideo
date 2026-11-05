# C017 — synthetic V1.0.2 failure regression fixture corpus

**Fixture origin: SYNTHETIC OFFLINE CASES, not recorded actual HTTP/codec incidents.** Do not present this as a confirmed V1.0.2 HTTP 403/timeout/codec fault. The real V1.0.2 screenshot `02.JPG` showed an unspecified thumbnail preview failure; its HTTP response and Windows Qt decoder diagnostics were not captured. V1.0.2 had no real video playback widget, therefore it could not produce a verified V1 `QMediaPlayer` codec-failure trace.

The source/reference facts were audited previously in `docs/RESEARCH_DECISIONS.md` using the verified C002 ZIP and `nvs/gui.py` / `nvs/providers.py`. The original ZIP, screenshot and user API keys are **not** included in this repository.

## Files

- `tests/fixtures/legacy_v102_failures.json` — versioned schema 1; explicit `fixture_type=synthetic_offline_reproduction`, historical observation/limitations, expected codes.
- `tests/test_legacy_regression.py` — offline replay with fake HTTP session (no external requests), synthetic FFmpeg/codec error signals, fake invalid MP4 header and Lake meeting false-positive oracle.
- `src/nature_video_studio/playback_diagnostics.py` — *signal-only* codec/error classifier for fixture testing. Not yet wired to `QMediaPlayer`; never emits original stderr, paths or secrets.

## Case coverage and distinction

| Failure family | Synthetic case IDs | What the test really proves |
| --- | --- | --- |
| HTTP failures | `http_403_forbidden`, `http_404_missing`, `http_429_rate_limit`, `http_502_upstream` | V2 poster-core `fetch_poster` returns differentiated status codes for mocked HTTP responses |
| Transport/TLS | `request_timeout`, `tls_certificate_failure`, `connection_reset` | Controlled `requests` exceptions map to distinct, non-sensitive codes |
| Image decoding proxies | `unexpected_html`, `corrupt_jpeg_magic`, `corrupt_png_magic`, `empty_jpeg` | Header/type-level rejection in the present poster core; **not** a real Qt `QPixmap.loadFromData()` decoder test |
| Security | `unsafe_redirect` | Cross-host redirect is refused in poster code |
| Video codec/container | `decoder_absent`, `unknown_fourcc`, `container_missing_moov`, `invalid_mp4`, `file_missing`, `undetermined_multimedia_error` | Synthetic FFmpeg-like error strings are classified. This **does not execute ffprobe**, check machine codec support, or replay actual video |
| Invalid MP4 bytes | `malformed_mp4_container_bytes` | Small truncated `ftyp` hex payload is materialized inside pytest tmpdir; no valid `moov`/`mdat` media; **not** a verified decoder crash |
| Lake meeting false positives | `archive_lake_council_meeting`, `archive_lake_school_board`, `archive_lake_title_ambiguous` | Naive Lake keyword matching incorrectly treats council/board or ambiguous titles as nature. These are **fictional** Archive-like item titles and IDs; they must be blocked/reviewed in R1 |
| Real nature control | `commons_lake_nature` | Fixture oracle distinguishes a synthetic landscape from a meeting; evidence is fabricated for testing, not genuine media verification |

**Known R1 gap:** the existing `filter_candidates` checks duration/resolution but does not enforce that `nature_relevance_verified` is true. The regression corpus documents the expected semantic outcome without freezing this bug as a required behavior. Actual item-level nature suitability evidence and relevance rejection are separate R1 acceptance criteria.

## Repeatable reproduction instructions

Use a clean Python >=3.11 environment on Windows or Linux. Run from repository checkout on feature branch:

```sh
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_legacy_regression.py
python -m pytest -vv tests/test_legacy_regression.py
python -m pytest -q
```

1. Pytest loads `legacy_v102_failures.json`; rejects duplicate IDs/schema mismatch and confirms synthetic provenance.
2. Each fake HTTP case is sent to `fetch_poster` through a deterministic in-memory `FakeSession`. Network access is **never** permitted; no Pexels/Pixabay credentials are read. Assert returned error code, no file cached on failed poster requests, no redirects to unsafe hosts.
3. Each synthetic codec/FFmpeg stderr string is passed to `classify_playback_failure` and compared with `expected_code`; no raw stderr or arbitrary private token is included in the returned status.
4. Invalid MP4 hex bytes are written **only into a pytest-owned temporary directory** to establish a reproducible malformed-file input. No codec is probed.
5. Synthetic Lake council/board rows are compared with a deliberately naive `"lake" in title` selector. The selector erroneously admits meetings. The manifest oracle requires reject/review, and the existing duration/resolution filter is observed without asserting its currently incomplete nature relevance semantics as correct behavior.
6. After any future R1/R2 implementation, expand these tests to verify the actual post-filter and the Windows Qt multimedia signals without replacing these historical surrogate samples by a false claim of V1 evidence.

No user Windows action is necessary for the synthetic test suite. An independent **real V1.0.2 replay** will require an explicitly authorized, isolated runtime session and sanitized logs, not user API keys or live unauthorized downloads.

## Follow-up real evidence needed before full C017 historical failure closure

- **Poster:** Actual V1.0.2 `QNetworkReply` error code, HTTP status, response content type/size and Qt image decode result with a controlled local mock server, using non-sensitive logs. The existing `02.JPG` only proves a generic preview failure.
- **Codec:** Because original V1 lacked a player, there is no meaningful "V1 codec failure" to reproduce. Instead record a *new V2 Windows Qt* playback result from an original, locally generated sample and a known unsupported/invalid synthetic file. Capture `QMediaPlayer.errorOccurred`, probe metadata (where supported), and record PASS/FAIL/SKIP by codec. No copyrighted sample bundled.
- **Relevance:** Replay an authorized Archive metadata fixture from officially accessible API with source URL, redacted title/license evidence, duration, nature/no-nature annotation and user approval. Do not claim the fictional meeting titles are real item identifiers.
- **Windows GUI:** Capture thumbnail/error UI, play/pause/seek status and distinguish an image failure from a video playback failure.

### C017 acceptance state

**Synthetic offline fixture coverage + replay pytest: measurable once CI confirms.** The user's three-point final acceptance of *existing V1 failure reproduction dataset* remains **PARTIAL** until historical/real Windows evidence and a real codec-reproduction sample are supplied. A passing mocked suite is **not** proof that V1's unknown 02.JPG error root cause was identified, or that V2 preview is fixed.
