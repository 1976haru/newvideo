"""C011: version truthfulness and non-confusable trial window title."""
import pytest

from nature_video_studio import __version__
from nature_video_studio.version_identity import (
    AppIdentity, V1_VERSION, V2_IDENTITY, validate_trial_identity,
)


def test_trial_window_title_contains_unambiguous_id():
    validate_trial_identity()
    assert V2_IDENTITY.version == __version__
    title = V2_IDENTITY.window_title
    assert title.startswith("[V2 시험판]")
    assert f"v{__version__}" in title
    assert "기존 V1.0.2 아님" in title
    assert "V1.0.2" in title
    assert V1_VERSION != __version__


def test_developer_trial_warning_blocks_feature_claims():
    assert "개발·검증용" in V2_IDENTITY.caution
    assert "변경하지 않습니다" in V2_IDENTITY.caution
    assert "연결되지 않았습니다" in V2_IDENTITY.caution


@pytest.mark.parametrize("identity", [
    AppIdentity("Nature Video Studio", "1.0.2", True),
    AppIdentity("Nature Video Studio", "2.0.0.dev0", False),
])
def test_version_is_explicit_never_legacy_alias(identity):
    if identity.trial:
        with pytest.raises(ValueError):
            validate_trial_identity(identity)
    else:
        validate_trial_identity(identity)
        assert "시험판" not in identity.window_title


def test_version_heading_explicit_trial():
    assert f"v{__version__}" in V2_IDENTITY.heading
    assert "시험판" in V2_IDENTITY.heading
