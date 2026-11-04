import pytest
from nature_video_studio.rights import RightsState, license_triage


@pytest.mark.parametrize("url,expected", [
    ("", RightsState.BLOCKED),
    ("https://creativecommons.org/publicdomain/zero/1.0/", RightsState.GENERAL_REVIEW),
    ("https://creativecommons.org/licenses/by/4.0/", RightsState.ATTRIBUTION_REVIEW),
    ("https://creativecommons.org/licenses/by-sa/4.0/", RightsState.ATTRIBUTION_REVIEW),
    ("https://creativecommons.org/licenses/by-nc/4.0/", RightsState.BLOCKED),
    ("https://creativecommons.org/licenses/by-nd/4.0/", RightsState.BLOCKED),
    ("https://creativecommons.org/licenses/by-nc-sa/4.0/", RightsState.BLOCKED),
    ("https://creativecommons.org/licenses/by-nc-nd/4.0/", RightsState.BLOCKED),
    ("https://notcreativecommons.org/licenses/by/4.0/", RightsState.BLOCKED),
    ("https://creativecommons.org/licenses/by/2.0/", RightsState.BLOCKED),
])
def test_cc_triage(url,expected):
    actual=license_triage(url)
    assert actual.status == expected
    assert not actual.can_auto_download


def test_pexels_general_license_requires_review():
    assert license_triage("https://www.pexels.com/license/","Pexels").status == RightsState.GENERAL_REVIEW


def test_pixabay_general_license_requires_review():
    assert license_triage("https://pixabay.com/service/license-summary/","Pixabay").status == RightsState.GENERAL_REVIEW


def test_forged_pexels_license_is_blocked():
    assert license_triage("https://pexels.com.evil.example/license/","Pexels").status == RightsState.BLOCKED


def test_rights_do_not_auto_approve_by_license_only():
    assert not license_triage("https://creativecommons.org/publicdomain/mark/1.0/").can_auto_download
