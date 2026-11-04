import pytest
from nature_video_studio.models import MediaCandidate, Rendition, SearchMode, ResolutionMode
from nature_video_studio.filtering import SearchCriteria, duration_reason, filter_candidates, resolution_reason
from nature_video_studio.sources import default_providers


def item(duration, verified=True, width=3840, height=2160, name="123"):
    return MediaCandidate(
        provider="fixture", source_id=name, source_url="https://example.org/media/123",
        title="lake nature", duration_seconds=duration, original_duration_verified=verified,
        renditions=(Rendition(width=width, height=height),), nature_relevance_verified=True
    )


@pytest.mark.parametrize("duration,expected", [
    (None,"원본 길이 미확인"),
    (0,"원본 길이 미달"),
    (10,"원본 길이 미달"),
    (60,"원본 길이 미달"),
    (120,"원본 길이 미달"),
    (179.999,"원본 길이 미달"),
    (180,None),
    (181,None),
    (1800,None),
])
def test_long_take_boundary(duration, expected):
    assert duration_reason(item(duration), SearchCriteria()) == expected


def test_unverified_assembled_length_is_not_original():
    assert duration_reason(item(600, verified=False), SearchCriteria()) == "원본 길이 미확인"


def test_short_mode_accepts_12_second_clip_only_in_short_lane():
    cand = item(12)
    assert duration_reason(cand, SearchCriteria(mode=SearchMode.SHORT_COMPOSER)) is None
    assert duration_reason(cand, SearchCriteria()) is not None


def test_four_k_uses_actual_rendition_not_original_marketing():
    assert resolution_reason(item(200, width=1920, height=1080), SearchCriteria(resolution=ResolutionMode.FOUR_K_ONLY)) == "4K 원본 파일 없음"


def test_four_k_preferred_can_show_fhd_with_correct_label():
    c = item(200, width=1920, height=1080)
    accepted, _ = filter_candidates([c], SearchCriteria())
    assert accepted == [c]
    assert c.max_resolution == (1920, 1080)


def test_180_second_min_with_optional_upper_cap():
    criteria = SearchCriteria(min_original_duration_seconds=180, max_original_duration_seconds=600)
    assert duration_reason(item(601), criteria) == "원본 길이 초과"
    assert duration_reason(item(600), criteria) is None


def test_invalid_duration_criteria():
    with pytest.raises(ValueError):
        SearchCriteria(min_original_duration_seconds=180, max_original_duration_seconds=179)


def test_long_take_default_provider_selection():
    assert "Pexels" not in default_providers(True)
    assert "Pexels" in default_providers(False)


def test_results_are_dedicated_to_long_lane():
    accepted, rejected = filter_candidates([item(40,name="short"), item(180,name="long")], SearchCriteria())
    assert [x.source_id for x in accepted] == ["long"]
    assert "fixture:short" in rejected
