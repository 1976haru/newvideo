"""C020 module boundary/contract tests (headless, deterministic, no real user data)."""
from __future__ import annotations

import ast
import asyncio
import threading
from pathlib import Path

import pytest

from nature_video_studio.catalog import UnavailableCatalog
from nature_video_studio.composer import CompositionPlan, UnavailableComposer
from nature_video_studio.download_queue import DownloadIntent, UnavailableDownloadQueue
from nature_video_studio.filtering import SearchCriteria
from nature_video_studio.models import MediaCandidate, Rendition, SearchMode
from nature_video_studio.preview import PreviewResult
from nature_video_studio.preview_service import PreviewService
from nature_video_studio.rights import RightsState, RightsDecision
from nature_video_studio.rights_review import RightsReview
from nature_video_studio.search_coordinator import SearchCoordinator
from nature_video_studio.service_errors import FeatureUnavailable
from nature_video_studio.source_adapter import SearchPage, SearchQuery


SERVICE_FILES = (
    "source_adapter", "search_coordinator", "preview_service", "rights_review",
    "download_queue", "catalog", "composer",
)
# Current V2 core is flat; explicit AST allowlists enforce dependency direction
# and forbid importing Qt/network/SQLite/rendering from these boundaries.
INTERNAL_ALLOWED = {
    "source_adapter": {"filtering", "models"},
    "search_coordinator": {"filtering", "models", "source_adapter"},
    "preview_service": {"preview"},
    "rights_review": {"models", "rights"},
    "download_queue": {"rights", "service_errors", "network_security"},
    "catalog": {"models", "service_errors"},
    "composer": {"service_errors"},
}
FORBIDDEN_EXTERNAL = {
    "PySide6", "requests", "sqlite3", "keyring", "subprocess",
    "httpx", "urllib.request", "shutil",
}


def scenic(provider: str, name: str, duration: float | None, verified=True):
    return MediaCandidate(
        provider=provider, source_id=name,
        source_url="https://example.org/source",
        title="호수 풍경", duration_seconds=duration,
        original_duration_verified=verified,
        renditions=(Rendition(3840, 2160),),
        nature_relevance_verified=True,
    )


class FakeAdapter:
    def __init__(self, name, supported_modes, candidates=(), error=None):
        self.name = name
        self.supported_modes = frozenset(supported_modes)
        self.candidates = tuple(candidates)
        self.error = error
        self.call_count = 0

    async def search(self, query):
        self.call_count += 1
        await asyncio.sleep(0)
        if self.error:
            raise self.error
        return SearchPage(provider=self.name, candidates=self.candidates)


def test_c020_all_seven_service_files_are_present():
    import nature_video_studio
    base = Path(nature_video_studio.__file__).parent
    assert all((base / (name + ".py")).is_file() for name in SERVICE_FILES)


@pytest.mark.parametrize("module_name", SERVICE_FILES)
def test_c020_forbid_cross_service_imports_and_blocking_gui_dependencies(module_name):
    import nature_video_studio
    p = Path(nature_video_studio.__file__).parent / (module_name + ".py")
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in FORBIDDEN_EXTERNAL, (module_name, alias.name)
                if root == "nature_video_studio":
                    direct = alias.name.split(".")[1:2]
                    assert not direct or direct[0] in INTERNAL_ALLOWED[module_name]
        if isinstance(node, ast.ImportFrom):
            target = node.module or ""
            root = target.split(".")[0]
            assert root not in FORBIDDEN_EXTERNAL, (module_name, target)
            if node.level > 0:
                assert root in INTERNAL_ALLOWED[module_name], (module_name, target)
            if root == "nature_video_studio" and node.level == 0:
                assert target.split(".")[1] in INTERNAL_ALLOWED[module_name]


def test_c020_long_search_is_strict_and_never_falls_back_to_short_adapter():
    long_source = FakeAdapter(
        "Wikimedia Commons", {SearchMode.LONG_ORIGINAL},
        [scenic("Wikimedia Commons", "179", 179),
         scenic("Wikimedia Commons", "180", 180),
         scenic("Wikimedia Commons", "unknown", 300, verified=False)],
    )
    short_source = FakeAdapter(
        "Pexels", {SearchMode.SHORT_COMPOSER},
        [scenic("Pexels", "15", 15)]
    )
    outcome = asyncio.run(SearchCoordinator([short_source, long_source])
                          .search(SearchQuery("호수")))
    assert [c.source_id for c in outcome.accepted] == ["180"]
    assert set(outcome.rejected) == {
        "Wikimedia Commons:179", "Wikimedia Commons:unknown",
    }
    assert short_source.call_count == 0
    assert long_source.call_count == 1
    assert [(s.provider, s.code) for s in outcome.providers] == [
        ("Pexels", "MODE_UNSUPPORTED"), ("Wikimedia Commons", "OK"),
    ]


def test_c020_short_search_is_separate_and_does_not_use_long_provider():
    short_source = FakeAdapter(
        "Pexels", {SearchMode.SHORT_COMPOSER},
        [scenic("Pexels", "15", 15)]
    )
    long_source = FakeAdapter("Wikimedia Commons", {SearchMode.LONG_ORIGINAL})
    outcome = asyncio.run(SearchCoordinator([long_source, short_source]).search(
        SearchQuery("湖", SearchCriteria(mode=SearchMode.SHORT_COMPOSER))
    ))
    assert [x.source_id for x in outcome.accepted] == ["15"]
    assert long_source.call_count == 0


def test_c020_one_provider_failure_does_not_destroy_others_or_expose_keys():
    secret = "PRIVATE_API_KEY_WOULD_BE_IN_EXCEPTION"
    failed = FakeAdapter("Internet Archive", {SearchMode.LONG_ORIGINAL},
                         error=RuntimeError(secret))
    good = FakeAdapter("Wikimedia Commons", {SearchMode.LONG_ORIGINAL},
                       [scenic("Wikimedia Commons", "180", 180)])
    result = asyncio.run(SearchCoordinator([failed, good]).search(SearchQuery("lake")))
    assert len(result.accepted) == 1
    assert [(x.provider, x.code) for x in result.providers] == [
        ("Internet Archive", "PROVIDER_FAILED"), ("Wikimedia Commons", "OK")]
    assert secret not in repr(result)


def test_c020_invalid_adapter_result_is_not_accepted():
    class WrongProvider(FakeAdapter):
        async def search(self, query):
            return SearchPage("Wrong provider", (scenic("Pexels", "a", 250),))
    result = asyncio.run(SearchCoordinator([
        WrongProvider("Pexels", {SearchMode.LONG_ORIGINAL})
    ]).search(SearchQuery("lake")))
    assert not result.accepted
    assert result.providers[0].code == "INVALID_PROVIDER_RESULT"


def test_c020_reject_duplicate_provider_names():
    a = FakeAdapter("Pexels", {SearchMode.SHORT_COMPOSER})
    with pytest.raises(ValueError, match="Duplicate"):
        SearchCoordinator([a, a])


def test_c020_empty_long_results_stay_empty_no_fake_search():
    result = asyncio.run(SearchCoordinator([]).search(SearchQuery("호수")))
    assert result.accepted == ()
    assert result.providers == ()


@pytest.mark.parametrize("query", ["", " ", "\n"])
def test_c020_reject_blank_search_request(query):
    with pytest.raises(ValueError):
        SearchQuery(query)


def test_c020_poster_runs_off_calling_event_loop_thread(tmp_path):
    main_thread = threading.get_ident()
    observed = []
    def fake_fetch(url, provider, cache_dir, session):
        observed.append(threading.get_ident())
        assert cache_dir == tmp_path / "V2_cache"
        return PreviewResult(None, "PREVIEW_HTTP_403", "simulated")
    result = asyncio.run(PreviewService(tmp_path / "V2_cache", fake_fetch)
                         .poster("https://images.pexels.com/fake.jpg", "Pexels"))
    assert result.code == "PREVIEW_HTTP_403"
    assert observed and observed[0] != main_thread
    assert not (tmp_path / "V2_cache").exists()


def test_c020_rights_review_never_auto_approves_licenses():
    review = RightsReview()
    cc_by = scenic("Wikimedia Commons", "license", 181)
    cc_by = MediaCandidate(
        **{**cc_by.__dict__,
           "license_url": "https://creativecommons.org/licenses/by/4.0/"}
    )
    status = review.triage(cc_by)
    assert status.status == RightsState.ATTRIBUTION_REVIEW
    assert not status.can_auto_download


def test_c020_download_requires_user_selection_and_review():
    reviewed = RightsDecision(RightsState.USER_VERIFIED, "reviewed", False)
    pending = RightsDecision(RightsState.GENERAL_REVIEW, "pending", False)
    with pytest.raises(ValueError):
        DownloadIntent("Pexels:123", False, reviewed)
    with pytest.raises(ValueError):
        DownloadIntent("Pexels:123", True, pending)
    intent = DownloadIntent("Wikimedia Commons:example", True, reviewed)
    with pytest.raises(FeatureUnavailable, match="not implemented"):
        asyncio.run(UnavailableDownloadQueue().enqueue(intent))


def test_c020_catalog_and_composer_ports_fail_closed():
    with pytest.raises(FeatureUnavailable, match="not implemented"):
        asyncio.run(UnavailableCatalog().find("test:lake"))
    with pytest.raises(FeatureUnavailable, match="not implemented"):
        asyncio.run(UnavailableCatalog().record(scenic("fixture", "a", 185)))
    with pytest.raises(ValueError):
        CompositionPlan(("fixture:a",), 7)
    with pytest.raises(ValueError):
        CompositionPlan((), 30)
    with pytest.raises(FeatureUnavailable, match="not implemented"):
        asyncio.run(UnavailableComposer().render(CompositionPlan(("fixture:a",), 20)))
