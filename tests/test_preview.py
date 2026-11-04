from pathlib import Path
from nature_video_studio.preview import fetch_poster, host_allowed


class MockResponse:
    def __init__(self, status=200, content=bytes.fromhex("ffd8") + b"xyz", content_type="image/jpeg", **headers):
        self.status_code = status
        self.headers = {"Content-Type": content_type, **headers}
        self.content = content
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False
    def iter_content(self,chunk_size):
        yield self.content


class MockSession:
    def __init__(self,responses):
        self.responses = list(responses)
        self.calls = 0
    def get(self, *args, **kwargs):
        self.calls += 1
        assert kwargs.get("allow_redirects") is False
        return self.responses.pop(0)


def test_provider_host_allowlist():
    assert host_allowed("https://images.pexels.com/video.jpg", "Pexels")
    assert host_allowed("https://cdn.pixabay.com/v.jpg", "Pixabay")
    assert not host_allowed("http://images.pexels.com/video.jpg", "Pexels")
    assert not host_allowed("https://images.pexels.com.evil.test/image.jpg", "Pexels")
    assert not host_allowed("https://127.0.0.1/private.jpg", "Pexels")
    assert not host_allowed("https://images.pexels.com:444/image.jpg", "Pexels")


def test_poster_success_and_cache(tmp_path):
    url="https://images.pexels.com/video.jpg"
    s=MockSession([MockResponse()])
    one=fetch_poster(url,"Pexels",tmp_path,s)
    assert one.code == "OK"
    assert one.path and one.path.read_bytes().startswith(bytes.fromhex("ffd8"))
    again=fetch_poster(url,"Pexels",tmp_path,s)
    assert again.from_cache
    assert s.calls == 1


def test_http_403_diagnostic(tmp_path):
    r=fetch_poster("https://images.pexels.com/v.jpg","Pexels",tmp_path,MockSession([MockResponse(status=403)]))
    assert r.code == "PREVIEW_HTTP_403"


def test_non_image_is_rejected(tmp_path):
    r=fetch_poster("https://images.pexels.com/v.jpg","Pexels",tmp_path,MockSession([MockResponse(content_type="text/html")]))
    assert r.code == "PREVIEW_NOT_IMAGE"


def test_invalid_jpeg_is_rejected(tmp_path):
    r=fetch_poster("https://images.pexels.com/v.jpg","Pexels",tmp_path,MockSession([MockResponse(content=b"<html>")]))
    assert r.code == "PREVIEW_INVALID_IMAGE"


def test_bad_redirect_blocked(tmp_path):
    a=MockResponse(status=302, Location="https://evil.example/steal")
    r=fetch_poster("https://images.pexels.com/v.jpg","Pexels",tmp_path,MockSession([a]))
    assert r.code == "PREVIEW_BAD_REDIRECT"


def test_oversize_rejected(tmp_path):
    r=fetch_poster("https://images.pexels.com/v.jpg","Pexels",tmp_path,
                   MockSession([MockResponse(**{"Content-Length": str(100_000_000)})]))
    assert r.code == "PREVIEW_TOO_BIG"


def test_cache_key_is_provider_and_url_sensitive(tmp_path):
    a=fetch_poster("https://cdn.pixabay.com/a.jpg","Pixabay",tmp_path,MockSession([MockResponse()]))
    b=fetch_poster("https://cdn.pixabay.com/b.jpg","Pixabay",tmp_path,MockSession([MockResponse()]))
    assert a.path != b.path
