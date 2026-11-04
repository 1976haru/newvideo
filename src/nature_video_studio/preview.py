"""Bounded poster fetcher. Preview image success is not video playback success."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urljoin, urlparse
import os

import requests

MAX_POSTER_BYTES = 8 * 1024 * 1024
MAX_REDIRECTS = 3
ALLOWED_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
PROVIDER_DOMAINS = {
    "Pexels": ("pexels.com",),
    "Pixabay": ("pixabay.com",),
    "Wikimedia Commons": ("wikimedia.org", "wikipedia.org"),
    "Internet Archive": ("archive.org",),
}


@dataclass(frozen=True)
class PreviewResult:
    path: Path | None
    code: str
    message: str
    from_cache: bool = False


def host_allowed(url: str, provider: str) -> bool:
    """Only HTTPS and explicitly documented provider domains. No credentials in URL."""
    p = urlparse(url)
    if p.scheme.lower() != "https" or p.username or p.password or not p.hostname or p.port not in (None, 443):
        return False
    hostname = p.hostname.lower()
    return any(hostname == d or hostname.endswith("." + d) for d in PROVIDER_DOMAINS.get(provider, ()))


def _filename(url: str, provider: str, mime: str) -> str:
    digest = sha256((provider + ":" + url).encode("utf-8")).hexdigest()
    return digest + ALLOWED_EXT[mime]


def fetch_poster(url: str, provider: str, cache_dir: Path, session=None) -> PreviewResult:
    """Download small image only. Explicit redirects, bounded bytes and error diagnostics.

    Network is synchronous: caller MUST invoke in a worker thread, never Qt GUI thread.
    This is intentionally a metadata/poster preview path; video playback is separate.
    """
    if not host_allowed(url, provider):
        return PreviewResult(None, "PREVIEW_BAD_URL", "허용되지 않은 미리보기 주소입니다.")
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = sha256((provider + ":" + url).encode("utf-8")).hexdigest()
    for mime, ext in ALLOWED_EXT.items():
        cached = cache_dir / (key + ext)
        if cached.is_file() and 0 < cached.stat().st_size <= MAX_POSTER_BYTES:
            return PreviewResult(cached, "OK", "캐시된 썸네일", True)

    session = session or requests.Session()
    current = url
    for attempt in range(MAX_REDIRECTS + 1):
        try:
            with session.get(current, timeout=(5, 15), stream=True,
                             allow_redirects=False,
                             headers={"User-Agent": "NatureVideoStudio/2.0 (desktop preview)"}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    dest = urljoin(current, response.headers.get("Location", ""))
                    if attempt == MAX_REDIRECTS:
                        return PreviewResult(None, "PREVIEW_REDIRECT", "미리보기 주소 이동이 너무 많습니다.")
                    if not host_allowed(dest, provider):
                        return PreviewResult(None, "PREVIEW_BAD_REDIRECT", "다른 사이트로 이동해 미리보기를 중단했습니다.")
                    current = dest
                    continue
                if response.status_code != 200:
                    return PreviewResult(None, f"PREVIEW_HTTP_{response.status_code}",
                                         f"썸네일 HTTP {response.status_code} 오류. 원본 페이지 또는 재시도를 사용하세요.")
                media_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                if media_type not in ALLOWED_EXT:
                    return PreviewResult(None, "PREVIEW_NOT_IMAGE", "서버가 이미지가 아닌 데이터를 보냈습니다.")
                size_header = response.headers.get("Content-Length")
                if size_header and int(size_header) > MAX_POSTER_BYTES:
                    return PreviewResult(None, "PREVIEW_TOO_BIG", "썸네일 최대 크기를 초과했습니다.")
                data = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    if len(data) + len(chunk) > MAX_POSTER_BYTES:
                        return PreviewResult(None, "PREVIEW_TOO_BIG", "썸네일 최대 크기를 초과했습니다.")
                    data.extend(chunk)
                if not data:
                    return PreviewResult(None, "PREVIEW_EMPTY", "서버에서 빈 이미지를 받았습니다.")
                if media_type == "image/jpeg" and not bytes(data).startswith(bytes.fromhex("ffd8")):
                    return PreviewResult(None, "PREVIEW_INVALID_IMAGE", "JPEG 데이터가 올바르지 않습니다.")
                if media_type == "image/png" and not bytes(data).startswith(bytes.fromhex("89504e470d0a1a0a")):
                    return PreviewResult(None, "PREVIEW_INVALID_IMAGE", "PNG 데이터가 올바르지 않습니다.")
                if media_type == "image/webp" and not (bytes(data).startswith(b"RIFF") and bytes(data)[8:12] == b"WEBP"):
                    return PreviewResult(None, "PREVIEW_INVALID_IMAGE", "WebP 데이터가 올바르지 않습니다.")
                dest = cache_dir / _filename(url, provider, media_type)
                tmp = None
                try:
                    with NamedTemporaryFile(dir=cache_dir, suffix=".part", delete=False) as out:
                        tmp = Path(out.name)
                        out.write(data)
                        out.flush()
                        os.fsync(out.fileno())
                    os.replace(tmp, dest)
                finally:
                    if tmp is not None and tmp.exists():
                        tmp.unlink()
                return PreviewResult(dest, "OK", "썸네일 저장")
        except requests.exceptions.Timeout:
            return PreviewResult(None, "PREVIEW_TIMEOUT", "서버 응답 시간이 초과되었습니다.")
        except requests.exceptions.SSLError:
            return PreviewResult(None, "PREVIEW_TLS", "보안 연결 인증 오류입니다.")
        except (requests.exceptions.RequestException, OSError, ValueError):
            return PreviewResult(None, "PREVIEW_NETWORK", "미리보기 네트워크 오류입니다. 원본 페이지를 확인하세요.")
    return PreviewResult(None, "PREVIEW_REDIRECT", "미리보기 주소 이동 오류입니다.")
