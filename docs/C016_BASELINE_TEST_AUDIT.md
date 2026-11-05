# C016 — R0 baseline tests: duration, 4K, rights

**Checklist verdict: PASS (2/2)** for the strictly scoped historical cross-platform **39-test baseline**. No new implementation is claimed. Completed status in the source checklist is independently verified against GitHub Actions job logs.

## Exact recorded evidence

- [GitHub Actions run #41918500325](https://github.com/1976haru/newvideo/actions/runs/41918500325)
- Event: `pull_request`; run head: `b774f0c1962f6dd6cfd832f60e6396412f76ce9b`
- GitHub run conclusion: `success`, all four test-matrix jobs completed successfully.
- Actual command, verified within each job log: `python -m pytest -q`

| Runner | Python | Job ID | Verified log result |
| --- | --- | ---: | --- |
| ubuntu-latest | 3.11 | 126884447229 | **39 passed in 0.20s** |
| windows-latest | 3.11 | 126884447642 | **39 passed in 0.18s** |
| ubuntu-latest | 3.12 | 126884447729 | **39 passed in 0.13s** |
| windows-latest | 3.12 | 126884447744 | **39 passed in 0.28s** |

No failures/skips appear in these four test summaries. The 39 count belongs specifically to the original Nov 5 baseline; **do not confuse it with the larger, subsequently added test suite**.

## Current feature-branch baseline code cross-check

Read the current source at `feature/v2-research-rebuild` (inspection head: `0fc6dfa92ffb7f2f5d5b8ea32c4c6f750c7618d1`):

- `tests/test_long_duration.py` and `src/nature_video_studio/filtering.py`: includes duration `None`, `0`, `10`, `60`, `120`, `179.999`, `180`, `181`, `1800`, original-duration verification flag, montage duration rejection and separate short lane. 180 seconds is inclusive for verified original duration; 179.999 seconds is rejected.
- `src/nature_video_studio/models.py`: `Rendition.is_4k` checks `width >= 3840` and `height >= 2160`; FHD-only rendition is rejected by `FOUR_K_ONLY`. For 4K preferred mode, FHD rendition may remain a candidate with its original 1920x1080 dimensions shown.
- `tests/test_rights.py` / `src/nature_video_studio/rights.py`: covers CC0/Public Domain Mark, CC BY, CC BY-SA, NC, ND, missing/forged URLs, Pexels/Pixabay general-license review; license triage alone does **not** grant automatic downloading.
- `docs/ACCEPTANCE.md` still requires actual media/file verification and Windows integrated tests before real V2 product acceptance.

## Important limitations / deferred gates

1. These tests use **synthetic MediaCandidate/rendition metadata**. A flag `original_duration_verified=True` within a fixture is **not proof** that an actual source is verified >=180 seconds; real provider adapters, authentic source metadata, and ffprobe on final files remain to be integrated/tested.
2. `Rendition.is_4k` is currently a numeric dimensions predicate, **not a forensic test of real captured 4K** and cannot detect upscaling. The R1/final-download gate must inspect actual decoded media and disclose original provenance without false 4K claims.
3. Conservative license URL classification is not a legal opinion or permission for YouTube commercial reuse. Third-party rights and selected-download consent remain for R3.
4. No claim is made here of live provider search, thumbnail GUI, streaming Qt playback, or a finished Windows EXE.
5. The current expanded suite has a successful CI run at `0fc6dfa92ffb7f2f5d5b8ea32c4c6f750c7618d1`: [#42122072956](https://github.com/1976haru/newvideo/actions/runs/42122072956), Windows Python 3.11 logs `150 passed, 1 skipped`, preservation gate `26 passed, 125 deselected`, dedicated Windows Qt smoke `6 passed`. Those are **separate later achievements**, not evidence that the historical 39-test figure changed.

## Governance and acceptance

C016 is a **historical foundation verification milestone**: 2/2 points, final PASS. Main branch remains at the previously observed initial SHA, the development branch stays `feature/v2-research-rebuild`, and Draft PR #1 remains unmerged. This document records the audit only; no user data, API keys, ZIP or real DB is touched.

**No user PC action necessary.** Next work: C017 audit, then R1 verification of real 180s original and resolution semantics, and R2 preview GUI.
