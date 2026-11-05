"""C017: safe, signal-only classification for mock multimedia error fixtures.

This does NOT decode videos, invoke ffprobe, or guarantee that a Qt backend
can play the given codec. Raw exception text may contain sensitive paths or
URLs: never log it, only the returned stable code and generic message.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlaybackDiagnosis:
    code: str
    message: str


_MESSAGES = {
    "PLAYBACK_CODEC_UNSUPPORTED": "동영상 코덱/디코더를 사용할 수 없습니다. 원본 파일 형식을 확인하세요.",
    "PLAYBACK_MEDIA_CORRUPT": "동영상 파일 데이터나 컨테이너가 손상되었을 수 있습니다.",
    "PLAYBACK_FILE_MISSING": "선택한 동영상 파일을 찾을 수 없습니다.",
    "PLAYBACK_UNKNOWN": "동영상 재생 오류입니다. 자세한 원인은 아직 확인되지 않았습니다.",
}


def classify_playback_failure(error_signal: str) -> PlaybackDiagnosis:
    """Classify common FFmpeg/Qt-like diagnostic text in a conservative order.

    Strings in the C017 corpus are purely synthetic, and this function is not
    yet wired into the production Qt player. Avoid inferring a particular
    machine's codec support from a synthetic string or from a file extension.
    """
    if not isinstance(error_signal, str):
        error_signal = ""
    text = error_signal.lower()
    if any(s in text for s in ("no such file or directory", "file does not exist")):
        code = "PLAYBACK_FILE_MISSING"
    elif any(s in text for s in (
        "moov atom not found", "invalid data found when processing input",
        "invalid media", "corrupt input",
    )):
        code = "PLAYBACK_MEDIA_CORRUPT"
    elif (
        "unsupported codec" in text
        or "unknown decoder" in text
        or ("decoder" in text and "not found" in text)
    ):
        code = "PLAYBACK_CODEC_UNSUPPORTED"
    else:
        code = "PLAYBACK_UNKNOWN"
    return PlaybackDiagnosis(code, _MESSAGES[code])
