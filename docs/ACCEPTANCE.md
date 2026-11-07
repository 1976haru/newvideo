# Acceptance criteria (must pass for real V2.0 release)

A. Search: 'lake nature', Long Take min 180s returns only candidates with verified original duration >=180. If 0, show 0 and explain. Test 179, 180, 181, missing, malformed, and 180 assembled from short clips. Only the single original 180/181 pass.
B. Resolution: 4K-only requires actual rendition >=3840x2160. FHD / unknown variants never mislabeled 4K.
C. Preview: poster displayed with cache on Windows; when 403/404/TLS/timeout/invalid image, UI says which failure + retry/source link. Local MP4 plays, pauses, seeks, mutes; test stale async replies.
D. Nature relevance: lake named government meetings are excluded; trustworthy scenic evidence needs more than keyword presence.
E. Rights: CC0, BY, BY-SA, NC, ND, blank, unknown cases tested. All display evidence/source and appropriate review/block state. No automatic promise of commercial approval.
F. Download: explicit selection/consent, allowed host and redirect, resume behavior, cancel, disk full, corrupted/partial files, duplicate hash, restore library on restart, API key redaction.
G. Editor: visibly different clips naturally connect; export durations are within 1s target, no silent audio mismatch, 15-song SRT cue begins at song start and lasts 12s.
H. Windows packaging: 10/11 x64 representative execution, fresh install with Python absent, D: absent, Korean/space path, Windows Defender unsigned warning documented, FFmpeg/PySide6 multimedia dependencies packaged.
I. QA: all available automated tests pass, real key limited search and approved sample download validated manually, GitHub Actions windows build green, SHA256/manifest published.
J. Policy: Pexels/Pixabay API attribution and caching; no unauthorized source redistribution, site bypass, or prohibited mass extraction.

No criterion can be marked PASS without reproducible command and evidence. SKIP and BLOCKED must be visible.
