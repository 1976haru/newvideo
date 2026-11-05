"""C011: one canonical identity for the unfinished V2 trial GUI.

Never reuse the V1 window caption, QSettings organization, icon or installer ID.
A stable 2.0 release MUST set trial=False and pass a separate release gate.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import __version__

V1_VERSION = "1.0.2"


@dataclass(frozen=True)
class AppIdentity:
    name: str
    version: str
    trial: bool

    @property
    def window_title(self) -> str:
        if self.trial:
            return f"[V2 시험판] {self.name} v{self.version} | 기존 V1.0.2 아님"
        return f"{self.name} v{self.version}"

    @property
    def heading(self) -> str:
        if self.trial:
            return f"Nature Video Studio V2.0.0 · 시험판"
        return f"Nature Video Studio v{self.version}"

    @property
    def caution(self) -> str:
        if self.trial:
            return (
                "이 창은 V2 개발·검증용 화면입니다.\n"
                "기존 V1.0.2 프로그램과 데이터는 변경하지 않습니다.\n"
                "영상 검색·다운로드·재생·편집은 아직 이 화면에 연결되지 않았습니다."
            )
        return "Nature Video Studio"


V2_IDENTITY = AppIdentity(
    name="Nature Video Studio",
    version=__version__,
    trial=True,
)


def validate_trial_identity(identity: AppIdentity = V2_IDENTITY) -> None:
    if identity.trial:
        if not identity.version.startswith("2."):
            raise ValueError("Trial must use V2 release series")
        if identity.version == V1_VERSION or "V1.0.2 아님" not in identity.window_title:
            raise ValueError("V1/V2 window titles cannot be confused")
        if "[V2 시험판]" not in identity.window_title:
            raise ValueError("Trial window must explicitly include a trial label")
    elif any(tag in identity.window_title for tag in ("시험판", "V1.0.2 아님")):
        raise ValueError("Stable version must not be falsely marked as a trial")
