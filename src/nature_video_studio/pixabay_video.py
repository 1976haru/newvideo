"""C029 Pixabay official *video* API metadata parser (offline, no network).

The API's "large" label is NOT proof of 4K: the documented example is
1920x1080.  This module checks each returned rendition's own URL, byte size,
width and height; no thumbnail, download or copyright clearance occurs here.

An API duration is verified as *provider-reported original metadata*, not
as an ffprobe measurement of the bytes. ffprobe evidence remains a separate
explicit gate for any "actual 4K file" assertion.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import math
from numbers import Real
from urllib.parse import urlsplit
from typing import Any, Mapping

from .models import MediaCandidate, Rendition
from .network_security import provider_url_allowed
from .source_adapter import SearchPage

PIXABAY_API_DOCS = "https://pixabay.com/api/docs/"
PIXABAY_CONTENT_TERMS = "https://pixabay.com/service/terms/"
PIXABAY_VIDEO_ENDPOINT = "https://pixabay.com/api/videos/"
PIXABAY_CACHE_TTL_SECONDS = 86400
PIXABAY_PROVIDER = "Pixabay"
_RENDITION_NAMES = ("large", "medium", "small", "tiny")


class PixabayPayloadError(ValueError):
    """An error code only; never include an API key, URL or response body."""


def _positive_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _positive_int(value: object, maximum: int) -> int | None:
    if type(value) is not int or not (0 < value <= maximum):
        return None
    return value


def _page_url(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 2048 or any(
        ord(c) < 33 or ord(c) == 127 for c in value
    ):
        return False
    try:
        p = urlsplit(value)
        return (
            p.scheme == "https"
            and p.hostname in ("pixabay.com", "www.pixabay.com")
            and p.port in (None, 443)
            and not p.username and not p.password and not p.fragment
            and not p.query and p.path.startswith("/videos/")
        )
    except (ValueError, TypeError):
        return False


def _rendition(raw: object) -> tuple[Rendition, str] | None:
    if not isinstance(raw, dict):
        return None
    url = raw.get("url")
    width = _positive_int(raw.get("width"), 16384)
    height = _positive_int(raw.get("height"), 16384)
    size = _positive_int(raw.get("size"), 1_000_000_000_000)
    if (
        not isinstance(url, str) or not provider_url_allowed(
            url, PIXABAY_PROVIDER, "download"
        ) or not urlsplit(url).path.lower().endswith(".mp4")
        or width is None or height is None or size is None
    ):
        return None
    poster = raw.get("thumbnail")
    if not provider_url_allowed(poster, PIXABAY_PROVIDER, "poster"):
        poster = ""
    return Rendition(width, height, media_url=url), poster


def parse_pixabay_video_hit(raw: object) -> MediaCandidate | None:
    """Make a candidate from documented API fields; return None for unsafe ID/page.

    An unknown/malformed duration is preserved as unverified and will be
    rejected by the existing >=180s and short-clips filters. It is never
    coerced to 180 or inferred from the number of stitched clips.
    """
    if not isinstance(raw, dict):
        return None
    video_id = _positive_int(raw.get("id"), 2**63 - 1)
    page_url = raw.get("pageURL")
    if video_id is None or not _page_url(page_url):
        return None
    raw_duration = _positive_number(raw.get("duration"))
    renditions_raw = raw.get("videos")
    renditions: list[Rendition] = []
    poster = ""
    large_is_valid = False
    large_reported_4k = False
    if isinstance(renditions_raw, dict):
        for name in _RENDITION_NAMES:
            rendition_data = _rendition(renditions_raw.get(name))
            if rendition_data is None:
                continue
            rendition, preview = rendition_data
            renditions.append(rendition)
            if not poster and preview:
                poster = preview
            if name == "large":
                large_is_valid = True
                large_reported_4k = rendition.is_4k

    tags = raw.get("tags")
    if not isinstance(tags, str):
        tags = ""
    title = tags.replace("\r", " ").replace("\n", " ").strip()[:120]
    user = raw.get("user")
    creator = user.strip()[:120] if isinstance(user, str) else ""
    large_note = (
        "large 메타데이터 4K 후보(실파일 ffprobe 미확인)"
        if large_reported_4k
        else "large 메타데이터 FHD/이하(4K 확정 불가)"
        if large_is_valid
        else "large 사용불가 또는 정보 불완전(4K 불인정)"
    )
    return MediaCandidate(
        provider=PIXABAY_PROVIDER,
        source_id=str(video_id),
        source_url=page_url,
        title=title or f"Pixabay video {video_id}",
        duration_seconds=raw_duration,
        original_duration_verified=raw_duration is not None,
        is_assembled=False,
        renditions=tuple(renditions),
        poster_url=poster,
        creator=creator,
        license_url=PIXABAY_CONTENT_TERMS,
        # Tags alone do not establish that the footage is a suitable landscape.
        nature_relevance_verified=False,
        notes=(
            "길이: Pixabay API 개별 동영상 metadata (실파일 미검증); "
            + large_note
            + "; 상업적 재사용/제3자 권리는 별도 검토"
        ),
    )


def parse_pixabay_video_response(payload: object) -> SearchPage:
    """Parse an already-authorized API response, not an arbitrary web page.

    No live request, API key handling, downloading, automated scraping,
    rights approval, or claim of actual pixel/fps verification.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("hits"), list):
        raise PixabayPayloadError("PIXABAY_INVALID_RESPONSE")
    hits = payload["hits"]
    if len(hits) > 200:
        raise PixabayPayloadError("PIXABAY_INVALID_RESPONSE")
    items = [parse_pixabay_video_hit(hit) for hit in hits]
    valid = tuple(item for item in items if item is not None)
    return SearchPage(provider=PIXABAY_PROVIDER, candidates=valid)


def _ffprobe_duration(payload: Mapping[str, Any]) -> float | None:
    fmt = payload.get("format")
    if not isinstance(fmt, dict):
        return None
    duration = fmt.get("duration")
    if isinstance(duration, bool):
        return None
    try:
        number = float(duration)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


@dataclass(frozen=True)
class PixabayFileEvidence:
    """Result of inspecting ffprobe JSON for the explicitly selected rendition."""
    width: int | None
    height: int | None
    duration_seconds: float | None
    reported_dimensions_match_file: bool
    duration_matches_api: bool
    verified_long_original: bool
    verified_4k_file: bool


def validate_pixabay_ffprobe(
    candidate: MediaCandidate, rendition: Rendition, probe: object
) -> PixabayFileEvidence:
    """Compare ffprobe output of an *authorized local video file* to API claims.

    This DOES NOT execute ffprobe, fetch a URL, validate that pixels were
    natively captured in 4K, or approve a video for YouTube reuse.
    """
    if candidate.provider != PIXABAY_PROVIDER or rendition not in candidate.renditions:
        raise PixabayPayloadError("PIXABAY_PROBE_SOURCE_MISMATCH")
    streams = probe.get("streams") if isinstance(probe, dict) else None
    stream = next(
        (s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"),
        None,
    ) if isinstance(streams, list) else None
    width = _positive_int(stream.get("width"), 16384) if stream else None
    height = _positive_int(stream.get("height"), 16384) if stream else None
    duration = _ffprobe_duration(probe) if isinstance(probe, dict) else None
    dimensions_match = (
        width is not None and height is not None
        and (width, height) == (rendition.width, rendition.height)
    )
    # Duration must not slip below the 180s gate due to rounding/tolerance.
    duration_match = (
        duration is not None and candidate.original_duration_verified
        and candidate.duration_seconds is not None
        and abs(duration - candidate.duration_seconds) <= 1.0
    )
    verified_long = bool(duration_match and duration >= 180 and not candidate.is_assembled)
    verified_4k = bool(
        dimensions_match and rendition.is_4k
        and width >= 3840 and height >= 2160
    )
    return PixabayFileEvidence(
        width, height, duration, dimensions_match, bool(duration_match),
        verified_long, verified_4k,
    )


def probe_pixabay_local_file(
    candidate: MediaCandidate, rendition: Rendition, file_path: str | Path,
    *, runner=None,
) -> PixabayFileEvidence:
    """Execute ffprobe safely on a user-approved, already-local MP4.

    This does not download, search, or touch any user library/database.
    A caller must first have selected the correct source file and reviewed
    rights; untrusted remote links are never passed to ffprobe.
    """
    if candidate.provider != PIXABAY_PROVIDER or rendition not in candidate.renditions:
        raise PixabayPayloadError("PIXABAY_PROBE_SOURCE_MISMATCH")
    try:
        target = Path(file_path)
        if target.suffix.lower() != ".mp4" or not target.is_file():
            raise PixabayPayloadError("PIXABAY_LOCAL_FILE_INVALID")
    except (TypeError, ValueError, OSError):
        raise PixabayPayloadError("PIXABAY_LOCAL_FILE_INVALID") from None

    # Argument vector (never shell=True); no raw stderr, paths or API tokens in
    # surfaced error messages. ffprobe is optional for this offline-only stage.
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,width,height:format=duration", "-of", "json",
        str(target),
    ]
    invoke = subprocess.run if runner is None else runner
    try:
        completed = invoke(
            command, capture_output=True, text=True, timeout=20, check=False,
        )
        if completed.returncode != 0 or not isinstance(completed.stdout, str):
            raise PixabayPayloadError("PIXABAY_FFPROBE_FAILED")
        if len(completed.stdout) > 131072:
            raise PixabayPayloadError("PIXABAY_FFPROBE_FAILED")
        payload = json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        raise PixabayPayloadError("PIXABAY_FFPROBE_FAILED") from None
    return validate_pixabay_ffprobe(candidate, rendition, payload)
