"""C021 SSRF, redirects, approved media URLs and secret redaction.

Completely offline. No real source requests, Windows keyring or user files.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import pytest

from nature_video_studio.download_queue import DownloadIntent, UnavailableDownloadQueue
from nature_video_studio.network_security import (
    UnsafeNetworkTarget, dns_is_public, provider_url_allowed,
    redact_sensitive, require_download_url,
)
from nature_video_studio.preview import fetch_poster, host_allowed
from nature_video_studio.rights import RightsDecision, RightsState
from nature_video_studio.service_errors import FeatureUnavailable


@pytest.mark.parametrize("provider,purpose,url", [
    ("Pexels", "poster", "https://images.pexels.com/photos/123/preview.jpeg"),
    ("Pexels", "download", "https://videos.pexels.com/video-files/123/video.mp4"),
    ("Pixabay", "poster", "https://cdn.pixabay.com/video/preview.jpg"),
    ("Pixabay", "download", "https://cdn.pixabay.com/video/clip.mp4"),
    ("Wikimedia Commons", "poster", "https://upload.wikimedia.org/wikipedia/commons/1/2/lake.jpg"),
    ("Wikimedia Commons", "download", "https://upload.wikimedia.org/wikipedia/commons/1/2/lake.webm"),
    ("Internet Archive", "poster", "https://archive.org/services/img/example"),
    ("Internet Archive", "download", "https://ia800012.us.archive.org/0/items/example/landscape.mp4"),
])
def test_security_allowed_official_media_hosts(provider, purpose, url):
    assert provider_url_allowed(url, provider, purpose)
    if purpose == "download":
        require_download_url(url, provider)
    else:
        assert host_allowed(url, provider)


@pytest.mark.parametrize("url", [
    "http://images.pexels.com/a.jpg",
    "file:///etc/passwd",
    "ftp://images.pexels.com/a.jpg",
    "https://localhost/private",
    "https://127.0.0.1/latest/meta-data/",
    "https://10.1.2.3/admin",
    "https://192.168.1.1/admin",
    "https://169.254.169.254/latest/meta-data/",
    "https://[::1]/admin",
    "https://images.pexels.com.evil.example/a.jpg",
    "https://other.images.pexels.com/a.jpg",
    "https://@images.pexels.com/a.jpg",  # empty URL userinfo bypass
    "https://user:secret@images.pexels.com/a.jpg",
    "https://images.pexels.com:444/a.jpg",
    "https://images.pexels.com:invalid/a.jpg",
    "https://[images.pexels.com/a.jpg",
    "https://images.pexels.com./a.jpg",
    "https://images.pexels.com/#fragment",
    "https://images.pexels.com\\@evil.example/a.jpg",
    "https://images.pexels.com\r\nX-Bad: yes/a.jpg",
    "https://images.pexels.com/%0d%0aX-Bad",
    "https://images.pexels.com/%00X-Bad",
    "https://images.pexels.com/../private",
    "https://images.pexels.com/%2e%2e/private",
    "https://images.pexels.com:443@evil.example/a.jpg",
    "https://images.pexels.com%40evil.example/a.jpg",
    "//images.pexels.com/a.jpg",
    "",
    " ",
])
def test_ssrf_bad_poster_urls_rejected_before_any_request(url, tmp_path):
    assert not host_allowed(url, "Pexels")
    class NoRequest:
        def get(self, *_a, **_k):
            raise AssertionError("network must never be touched for denied URL")
    result = fetch_poster(url, "Pexels", tmp_path / "cache", NoRequest())
    assert result.code == "PREVIEW_BAD_URL"
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("url,provider", [
    ("https://images.pexels.com/image.jpg", "Pexels"),  # image != video download host
    ("https://videos.pexels.com/media.mp4", "Pixabay"),  # incorrect provider
    ("https://www.youtube.com/watch?v=abc", "Internet Archive"),
    ("https://example.com/video.mp4", "Internet Archive"),
    ("http://ia800012.us.archive.org/file.mp4", "Internet Archive"),
    ("https://127.0.0.1/clip.mp4", "Internet Archive"),
    ("https://ia800012.us.archive.org:8080/file.mp4", "Internet Archive"),
    ("https://foo.archive.org.evil.test/file.mp4", "Internet Archive"),
    ("https://@ia800012.us.archive.org/file.mp4", "Internet Archive"),
])
def test_ssrf_arbitrary_download_url_denied(url, provider):
    with pytest.raises(UnsafeNetworkTarget) as e:
        require_download_url(url, provider)
    assert e.value.code == "URL_DISALLOWED"
    assert url not in str(e.value)


def _answer(ip):
    return (socket.AF_INET6 if ":" in ip else socket.AF_INET,
            socket.SOCK_STREAM, 0, "", (ip, 443))


@pytest.mark.parametrize("addresses,expected", [
    (["8.8.8.8"], True),
    (["8.8.8.8", "2001:4860:4860::8888"], True),
    (["127.0.0.1"], False),
    (["10.0.0.2"], False),
    (["192.168.0.10"], False),
    (["169.254.169.254"], False),
    (["100.64.0.1"], False),
    (["0.0.0.0"], False),
    (["::1"], False),
    (["fc00::1"], False),
    (["fe80::1"], False),
    (["::ffff:127.0.0.1"], False),
    (["8.8.8.8", "127.0.0.1"], False),
    ([], False),
])
def test_ssrf_dns_requires_all_public_answers(addresses, expected):
    result = dns_is_public(
        "https://images.pexels.com/photo.jpg",
        resolver=lambda *_args, **_kwargs: [_answer(ip) for ip in addresses]
    )
    assert result is expected


def test_ssrf_dns_failure_defaults_to_denied():
    def failing_resolver(*a, **k):
        raise socket.gaierror("synthetic lookup failed")
    assert not dns_is_public("https://images.pexels.com/a.jpg",
                             resolver=failing_resolver)


class FakeResponse:
    def __init__(self, status, data=b"\xff\xd8FAKE", **headers):
        self.status_code = status
        self.headers = {"Content-Type": "image/jpeg", **headers}
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def iter_content(self, chunk_size):
        yield self.data


class OwnedSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.trust_env = True
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True
        return self.responses.pop(0)

    def close(self):
        self.closed = True


def test_security_real_transport_disables_env_proxy_and_checks_dns_every_hop(
    tmp_path, monkeypatch
):
    import nature_video_studio.preview as module
    stub = OwnedSession([
        FakeResponse(302, Location="/second.jpg"),
        FakeResponse(200),
    ])
    checks = []
    def fake_dns(url):
        checks.append(url)
        return True
    monkeypatch.setattr(module.requests, "Session", lambda: stub)
    monkeypatch.setattr(module, "dns_is_public", fake_dns)
    first = "https://images.pexels.com/first.jpg"
    result = fetch_poster(first, "Pexels", tmp_path)
    assert result.code == "OK"
    assert checks == [first, "https://images.pexels.com/second.jpg"]
    assert len(stub.calls) == 2
    assert stub.trust_env is False
    assert stub.closed


def test_ssrf_public_to_private_dns_change_blocks_next_redirect(
    tmp_path, monkeypatch
):
    import nature_video_studio.preview as module
    stub = OwnedSession([FakeResponse(302, Location="/second.jpg")])
    checks = []
    def fake_dns(url):
        checks.append(url)
        return len(checks) == 1  # only first hop public
    monkeypatch.setattr(module.requests, "Session", lambda: stub)
    monkeypatch.setattr(module, "dns_is_public", fake_dns)
    result = fetch_poster("https://images.pexels.com/first.jpg", "Pexels", tmp_path)
    assert result.code == "PREVIEW_UNSAFE_DNS"
    assert len(stub.calls) == 1
    assert stub.closed


@pytest.mark.parametrize("destination", [
    "https://127.0.0.1/private",
    "http://images.pexels.com/insecure.jpg",
    "https://images.pexels.com.evil.test/path",
    "https://user:secret@images.pexels.com/a.jpg",
    "file:///etc/passwd",
    "https://images.pexels.com:444/a.jpg",
])
def test_ssrf_redirect_never_follows_unapproved_destination(tmp_path, destination):
    class OneHop:
        calls = 0
        def get(self, *_a, **_k):
            self.calls += 1
            if self.calls > 1:
                raise AssertionError("unsafe redirect was followed")
            return FakeResponse(302, Location=destination)
    transport = OneHop()
    result = fetch_poster(
        "https://images.pexels.com/start.jpg", "Pexels", tmp_path, transport)
    assert result.code == "PREVIEW_BAD_REDIRECT"
    assert transport.calls == 1


@pytest.mark.parametrize("sample,leaked", [
    ("Authorization: Bearer TOP_SECRET_123", "TOP_SECRET_123"),
    ("Proxy-Authorization: Basic VeryPrivate", "VeryPrivate"),
    ("api_key=pexels-secret-ABC123", "pexels-secret-ABC123"),
    ("access_token:tok_sensitive_value", "tok_sensitive_value"),
    ('{"api_key":"json_secret_123"}', "json_secret_123"),
    ("https://images.pexels.com/a.jpg?X-Amz-Signature=SignedPrivate", "SignedPrivate"),
    ("https://user:pass@images.pexels.com/private.jpg", "user:pass"),
])
def test_redact_never_exposes_fixture_secret(sample, leaked):
    output = redact_sensitive(sample)
    assert leaked not in output
    assert "[REDACTED]" in output or "[URL_REDACTED]" in output


def test_redact_nonstring_and_mixed_headers():
    assert redact_sensitive({"api_key": "dummy"}) == "[REDACTED NON-TEXT]"
    result = redact_sensitive(
        "Authorization: Bearer TOKEN_1\n"
        "https://cdn.pixabay.com/a.jpg?auth=TOKEN_2&sig=TOKEN_3\n"
        '{"password":"TOKEN_4"}'
    )
    assert all(token not in result for token in ("TOKEN_1", "TOKEN_2", "TOKEN_3", "TOKEN_4"))


def test_security_download_intent_requires_selected_approved_url_and_rights():
    review = RightsDecision(RightsState.USER_VERIFIED, "human reviewed", False)
    allowed = "https://upload.wikimedia.org/wikipedia/commons/a/landscape.webm"
    intent = DownloadIntent("Wikimedia Commons:landscape", True, review, allowed, "Wikimedia Commons")
    with pytest.raises(FeatureUnavailable):
        asyncio.run(UnavailableDownloadQueue().enqueue(intent))
    assert intent.provider == "Wikimedia Commons"
    with pytest.raises(ValueError):
        DownloadIntent("Wikimedia Commons:landscape", True, review, allowed, None)
    with pytest.raises(UnsafeNetworkTarget):
        DownloadIntent("Wikimedia Commons:landscape", True, review,
                       "https://localhost/admin", "Wikimedia Commons")
    with pytest.raises(ValueError):
        DownloadIntent("https://upload.wikimedia.org/video?token=secret", True, review)
    pending = RightsDecision(RightsState.ATTRIBUTION_REVIEW, "BY attribution", True)
    with pytest.raises(ValueError):
        DownloadIntent("Wikimedia Commons:landscape", True, pending, allowed, "Wikimedia Commons")
    with pytest.raises(ValueError):
        DownloadIntent("Wikimedia Commons:landscape", False, review, allowed, "Wikimedia Commons")


def test_security_no_automatic_download_or_real_credential_access(monkeypatch):
    import sys
    class Trap:
        def get_password(self, *a):
            raise AssertionError("must never read a real credential")
        def set_password(self, *a):
            raise AssertionError("must never write a real credential")
        def delete_password(self, *a):
            raise AssertionError("must never delete a real credential")
    monkeypatch.setitem(sys.modules, "keyring", Trap())
    review = RightsDecision(RightsState.USER_VERIFIED, "human reviewed", False)
    approved = DownloadIntent(
        "Internet Archive:lake123", True, review,
        "https://ia800012.us.archive.org/0/items/lake123/original.mp4",
        "Internet Archive")
    with pytest.raises(FeatureUnavailable):
        asyncio.run(UnavailableDownloadQueue().enqueue(approved))


def test_security_qt_backend_error_display_uses_safe_classifier_not_raw_detail():
    """Static headless guard; real Qt playback remains an R2 test."""
    from pathlib import Path
    import nature_video_studio
    file = Path(nature_video_studio.__file__).parent / "local_player.py"
    source = file.read_text(encoding="utf-8")
    compile(source, str(file), "exec")
    assert "classify_playback_failure(details or \"\")" in source
    assert "details or str(error)" not in source
    assert "diagnosis.code" in source and "diagnosis.message" in source
