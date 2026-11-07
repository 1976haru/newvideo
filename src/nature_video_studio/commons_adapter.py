"""C030 Wikimedia Commons long-original candidate adapter.

Official Action API: generator=search (namespace 6) + prop=videoinfo;
videoinfo and imageinfo MUST NOT be requested together. Explicit WebM
playtime_seconds and Ogg length are the only recognized duration evidence.
This adapter does NOT prove that the file is unedited or rights-cleared.
"""
from __future__ import annotations

import asyncio
from html import unescape
from html.parser import HTMLParser
import math
from numbers import Real
import re
from typing import Callable
from urllib.parse import quote, urlsplit

import requests

from .models import MediaCandidate, Rendition, SearchMode
from .network_security import provider_url_allowed
from .source_adapter import SearchPage, SearchQuery

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_NAME = "Wikimedia Commons"
COMMONS_DOCS = "https://www.mediawiki.org/wiki/Extension:TimedMediaHandler/API"
COMMONS_RIGHTS_DOCS = "https://commons.wikimedia.org/wiki/Commons:Machine-readable_data"
MAX_PAGE_SIZE = 5
MAX_BODY_BYTES = 2_000_000

class CommonsAdapterError(ValueError):
    """Stable failure code, without raw URLs, responses, or credentials."""


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)


def _clean_html(value: object) -> str:
    if not isinstance(value, str) or len(value) > 8192:
        return ""
    parser = _PlainText()
    try:
        parser.feed(value)
    except (ValueError, TypeError):
        return ""
    return re.sub(r"\s+", " ", unescape(" ".join(parser.parts))).strip()[:256]


def _float_positive(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (Real, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and 0 < number <= 86400 * 7 else None


def _int_positive(value: object) -> int | None:
    return value if type(value) is int and 0 < value <= 16384 else None


def _duration(metadata: object) -> float | None:
    """WebM uses playtime_seconds and Ogg length, not human-readable titles."""
    if not isinstance(metadata, list):
        return None
    values: list[float] = []
    for item in metadata:
        if isinstance(item, dict) and item.get("name") in (
            "playtime_seconds", "length"
        ):
            seconds = _float_positive(item.get("value"))
            if seconds is not None:
                values.append(seconds)
    # Conflicting metadata is not trusted.
    if not values or max(values) - min(values) > 1:
        return None
    return values[0]


def _license_url(ext: object) -> str:
    if not isinstance(ext, dict):
        return ""
    record = ext.get("LicenseUrl")
    if not isinstance(record, dict):
        return ""
    url = record.get("value")
    if not isinstance(url, str) or len(url) > 1024:
        return ""
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.username or p.password or p.query
            or p.fragment or p.port not in (None, 443)):
            return ""
        host = (p.hostname or "").lower()
        if host not in ("creativecommons.org", "commons.wikimedia.org",
                        "www.gnu.org"):
            return ""
    except (ValueError, TypeError):
        return ""
    return url


def _metadata_value(ext: object, name: str) -> str:
    if not isinstance(ext, dict) or not isinstance(ext.get(name), dict):
        return ""
    return _clean_html(ext[name].get("value"))


def _source_page(page: dict, vi: dict) -> str:
    url = vi.get("descriptionurl")
    if isinstance(url, str) and len(url) <= 2048:
        try:
            p = urlsplit(url)
            if (p.scheme == "https" and p.hostname == "commons.wikimedia.org"
                and p.port in (None, 443) and not p.username and not p.password
                and not p.query and not p.fragment and p.path.startswith("/wiki/File:")):
                return url
        except (ValueError, TypeError):
            pass
    title = page.get("title")
    if isinstance(title, str) and title.startswith("File:") and len(title) <= 512:
        return "https://commons.wikimedia.org/wiki/" + quote(
            title.replace(" ", "_"), safe=":()"
        )
    return ""


def commons_video_candidate(page: object) -> MediaCandidate | None:
    """Parse a file's videoinfo, rejecting nonvideo/unsafe media and pages."""
    if not isinstance(page, dict) or page.get("ns") != 6:
        return None
    title = page.get("title")
    if not isinstance(title, str) or not title.startswith("File:") or len(title) > 512:
        return None
    infos = page.get("videoinfo")
    if not isinstance(infos, list) or not infos or not isinstance(infos[0], dict):
        return None
    info = infos[0]
    if info.get("mediatype") != "VIDEO":
        return None
    if info.get("mime") not in ("video/webm", "video/ogg", "application/ogg", "video/mp4"):
        return None
    file_url = info.get("url")
    if not provider_url_allowed(file_url, COMMONS_NAME, "download"):
        return None
    source_url = _source_page(page, info)
    if not source_url:
        return None
    width = _int_positive(info.get("width"))
    height = _int_positive(info.get("height"))
    bytes_value = info.get("size")
    if (width is None or height is None or type(bytes_value) is not int
        or bytes_value <= 0):
        return None
    duration = _duration(info.get("metadata"))
    ext = info.get("extmetadata")
    artist = _metadata_value(ext, "Artist")
    license_url = _license_url(ext)
    license_name = _metadata_value(ext, "LicenseShortName")
    terms = _metadata_value(ext, "UsageTerms")
    thumb = info.get("thumburl")
    poster = thumb if provider_url_allowed(thumb, COMMONS_NAME, "poster") else ""
    return MediaCandidate(
        provider=COMMONS_NAME,
        source_id=title,
        source_url=source_url,
        title=title[5:].replace("_", " "),
        duration_seconds=duration,
        original_duration_verified=duration is not None,
        renditions=(Rendition(width, height, media_url=file_url),),
        poster_url=poster,
        creator=artist or _clean_html(info.get("user")),
        license_url=license_url,
        nature_relevance_verified=False,
        notes=(
            "Commons videoinfo 파일 메타데이터(실파일 ffprobe/원본 촬영 여부 미확인); "
            + ("길이 확인" if duration is not None else "원본 길이 미확인")
            + "; 라이선스 " + (license_name or "미확인")
            + "; 이용조건 " + (terms or "개별 확인 필요")
            + "; 상업 재사용·제3자 권리 별도 검토"
        ),
    )


def parse_commons_response(payload: object) -> SearchPage:
    if not isinstance(payload, dict) or "error" in payload:
        raise CommonsAdapterError("COMMONS_INVALID_RESPONSE")
    query = payload.get("query")
    pages = query.get("pages") if isinstance(query, dict) else None
    if not isinstance(pages, list) or len(pages) > MAX_PAGE_SIZE:
        raise CommonsAdapterError("COMMONS_INVALID_RESPONSE")
    candidates = tuple(
        candidate for page in pages
        if (candidate := commons_video_candidate(page)) is not None
    )
    continuation = payload.get("continue")
    offset = continuation.get("gsroffset") if isinstance(continuation, dict) else None
    cursor = str(offset) if type(offset) is int and 0 < offset <= 1000 else None
    return SearchPage(COMMONS_NAME, candidates, cursor)


def _fetch_official(params: dict[str, str]) -> dict:
    """Official HTTPS endpoint only, no redirects and a bounded JSON body."""
    try:
        response = requests.get(
            COMMONS_API,
            params=params,
            headers={
                "User-Agent": "NatureVideoStudio/2.0 (https://github.com/1976haru/newvideo; personal research)",
                "Accept": "application/json",
            },
            timeout=(5, 20),
            allow_redirects=False,
            stream=True,
        )
        try:
            if response.status_code in (429, 503):
                raise CommonsAdapterError("COMMONS_RATE_LIMIT")
            if response.status_code != 200:
                raise CommonsAdapterError("COMMONS_HTTP_ERROR")
            if "json" not in response.headers.get("Content-Type", "").lower():
                raise CommonsAdapterError("COMMONS_INVALID_CONTENT_TYPE")
            body = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                body.extend(chunk)
                if len(body) > MAX_BODY_BYTES:
                    raise CommonsAdapterError("COMMONS_RESPONSE_TOO_LARGE")
            payload = response.json() if False else None
            import json
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise CommonsAdapterError("COMMONS_INVALID_RESPONSE")
            return payload
        finally:
            response.close()
    except CommonsAdapterError:
        raise
    except (requests.RequestException, ValueError, UnicodeError, TimeoutError):
        raise CommonsAdapterError("COMMONS_REQUEST_FAILED") from None


class CommonsLongAdapter:
    """Injectable authorized Commons search; one bounded request per search.

    No QThread/Qt, arbitrary URLs, downloads, login, credentials or local data.
    The GUI is not wired to this adapter until a separate UI acceptance gate.
    """

    name = COMMONS_NAME
    supported_modes = frozenset({SearchMode.LONG_ORIGINAL})

    def __init__(self, fetch_json: Callable[[dict[str, str]], dict] | None = None):
        self._fetch_json = fetch_json or _fetch_official

    async def search(self, query: SearchQuery) -> SearchPage:
        if query.criteria.mode != SearchMode.LONG_ORIGINAL:
            raise CommonsAdapterError("COMMONS_MODE_UNSUPPORTED")
        if len(query.text) > 180 or "\x00" in query.text:
            raise CommonsAdapterError("COMMONS_INVALID_QUERY")
        params = {
            "action": "query", "format": "json", "formatversion": "2",
            "generator": "search", "gsrnamespace": "6",
            "gsrsearch": "filetype:video " + query.text.strip(),
            "gsrlimit": str(MAX_PAGE_SIZE),
            "prop": "videoinfo",
            "viprop": "url|size|mime|mediatype|metadata|extmetadata|user",
            "viurlwidth": "320",
            "viextmetadatafilter": "LicenseUrl|LicenseShortName|UsageTerms|Artist",
            "viextmetadatalanguage": "en",
            "vimetadataversion": "latest",
            "maxlag": "5",
        }
        if query.cursor is not None:
            if not query.cursor.isascii() or not query.cursor.isdigit():
                raise CommonsAdapterError("COMMONS_INVALID_CURSOR")
            offset = int(query.cursor)
            if not 0 < offset <= 1000:
                raise CommonsAdapterError("COMMONS_INVALID_CURSOR")
            params["gsroffset"] = str(offset)
        # All potentially blocking network I/O runs off the caller/GUI thread.
        result = await asyncio.to_thread(self._fetch_json, params)
        return parse_commons_response(result)
