"""C021: provider-bound HTTPS URLs, DNS risk checks and defensive log redaction.

Only approved media hostnames are eligible. This is an *allowlist preflight*,
not a complete SSRF sandbox: DNS could change between resolution and connect
unless a future transport pins/validates the actual remote peer. See C021 docs.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import unquote, urlsplit


# Explicit media hosts; no arbitrary www.example subdomains or external pages.
# Archive uses regional ia*.us.archive.org storage hosts, hence the suffix rule.
POSTER_HOSTS: dict[str, tuple[str, ...]] = {
    "Pexels": ("images.pexels.com",),
    "Pixabay": ("cdn.pixabay.com",),
    "Wikimedia Commons": ("upload.wikimedia.org", "commons.wikimedia.org"),
    "Internet Archive": ("archive.org", ".archive.org"),
}
DOWNLOAD_HOSTS: dict[str, tuple[str, ...]] = {
    "Pexels": ("videos.pexels.com",),
    "Pixabay": ("cdn.pixabay.com",),
    "Wikimedia Commons": ("upload.wikimedia.org",),
    "Internet Archive": ("archive.org", ".archive.org"),
}


class UnsafeNetworkTarget(ValueError):
    """Only a stable error code: never embed a user URL or credential."""
    def __init__(self, code: str):
        if code not in ("URL_DISALLOWED", "DNS_UNSAFE"):
            code = "URL_DISALLOWED"
        self.code = code
        super().__init__(code)


def _approved_hostname(host: str, approved: tuple[str, ...]) -> bool:
    return any(
        host.endswith(rule) and len(host) > len(rule)
        if rule.startswith(".") else host == rule
        for rule in approved
    )


def provider_url_allowed(url: str, provider: str, purpose: str = "poster") -> bool:
    """Strict HTTPS media URL authorization, no DNS calls or filesystem writes.

    Credential-bearing query strings may be required for some authorized file
    resources; they must NEVER be exposed in logs. Scheme, host, username,
    port, authority controls, path traversal and fragments fail closed.
    """
    if not isinstance(url, str) or len(url) > 4096 or not url:
        return False
    if "\\" in url or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        return False
    # Prevent encoded CR/LF/NUL payloads crossing network library boundaries.
    if re.search(r"%(?:00|0a|0d)", url, flags=re.IGNORECASE):
        return False
    table = {"poster": POSTER_HOSTS, "download": DOWNLOAD_HOSTS}.get(purpose)
    if table is None or provider not in table:
        return False
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or "@" in parsed.netloc
            or "%" in parsed.netloc
            or not host
            or parsed.port not in (None, 443)
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
        ):
            return False
        if not host.isascii() or not _approved_hostname(host.lower(), table[provider]):
            return False
        if host.endswith(".") or len(host) > 253:
            return False
        # Literal IPs, special domains and unapproved subdomains are all denied.
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            return False
        # Forbid plaintext, encoded or double-encoded path traversal and
        # control bytes. These must not be normalized by requests later.
        part = parsed.path
        for _ in range(3):
            if (
                re.search(r"(?:^|/)\.{2}(?:/|$)", part)
                or "\\" in part
                or any(ord(c) <= 31 or ord(c) == 127 for c in part)
            ):
                return False
            next_part = unquote(part)
            if next_part == part:
                break
            part = next_part
    except ValueError:
        return False
    return True


def require_download_url(url: str, provider: str) -> None:
    """Reusable R3 preflight; it performs no download and conveys no rights."""
    if not provider_url_allowed(url, provider, "download"):
        raise UnsafeNetworkTarget("URL_DISALLOWED")


def dns_is_public(url: str, *, resolver=None) -> bool:
    """Fail closed if any DNS answer is loopback/private/link-local/reserved.

    Actual HTTPS peer validation/pinning is still needed for full SSRF
    resistance. In unit tests resolver is deterministic, with no DNS access.
    """
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return False
        host = parsed.hostname
        if resolver is None:
            resolver = socket.getaddrinfo
        answers = resolver(host, 443, type=socket.SOCK_STREAM)
        if not answers:
            return False
        for answer in answers:
            address = answer[4][0].split("%", 1)[0]
            if not ipaddress.ip_address(address).is_global:
                return False
        return True
    except (OSError, ValueError, IndexError, TypeError, OverflowError):
        return False


# Defense in depth only: never emit raw URL, headers, token or exception.
_SECRET_PARAMS = re.compile(
    r"(?i)(?P<name>\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"id[_-]?token|authorization|auth|secret|password|passwd|"
    r"signature|sig|x-amz-signature|token|key)\s*[=:]\s*)"
    r"(?P<value>[^\s&;,'\"\]\}]+)"
)
_AUTH_HEADER = re.compile(
    r"(?i)(?P<name>\b(?:Authorization|Proxy-Authorization)\s*:\s*)"
    r"(?P<value>[^\r\n]+)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+={0,2}")
_JSON_SECRET = re.compile(
    r'(?i)(?P<prefix>"(?:api_key|apikey|access_token|refresh_token|token|'
    r'authorization|password|secret|signature|key)"\s*:\s*")'
    r'(?P<secret>[^"]*)(?P<suffix>")'
)
_URL_IN_LOG = re.compile(r'(?i)\bhttps?://[^\s<>"\x27]+')



def redact_sensitive(value: object) -> str:
    """Best-effort diagnostic sanitization; prefer stable codes over raw data."""
    if not isinstance(value, str):
        return "[REDACTED NON-TEXT]"
    output = _AUTH_HEADER.sub(lambda m: m.group("name") + "[REDACTED]", value)
    # Never emit a full query string, even with unrecognized signed-URL keys.
    output = _URL_IN_LOG.sub("[URL_REDACTED]", output)
    output = _BEARER.sub("Bearer [REDACTED]", output)
    output = _JSON_SECRET.sub(
        lambda m: m.group("prefix") + "[REDACTED]" + m.group("suffix"), output
    )
    output = _SECRET_PARAMS.sub(lambda m: m.group("name") + "[REDACTED]", output)
    return output
