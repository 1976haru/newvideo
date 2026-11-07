"""Live provider search widgets for the existing V2 GUI.

Actual search is performed only after a user click, on the inherited QThread.
No provider keys, downloads, cookies or login are stored in SQLite or files.
Thumbnail fetch is an independent bounded worker; playback is NOT implemented.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from .models import SearchMode
from .preview import PreviewResult
from .preview_service import PreviewService
from .rights import license_triage
from .search_tabs import SearchTabsWidget, _time_text

STATUS_MESSAGES = {
    "OK": "정상 응답",
    "API_KEY_MISSING": "Pixabay API 키 없음: 기존 보안 저장소 확인 또는 이번 실행용 키 입력",
    "KEYRING_ERROR": "Windows 보안 저장소 접근 오류",
    "KEYRING_UNAVAILABLE": "보안 저장소 모듈 미설치",
    "PIXABAY_RATE_LIMIT": "Pixabay 요청 제한: 잠시 후 재시도",
    "PIXABAY_HTTP_ERROR": "Pixabay HTTP 오류",
    "PIXABAY_NETWORK_ERROR": "Pixabay 네트워크/TLS/시간 초과",
    "PIXABAY_INVALID_RESPONSE": "Pixabay 응답 형식 오류",
    "COMMONS_RATE_LIMIT": "Commons 서버 제한: 나중에 재시도",
    "COMMONS_HTTP_ERROR": "Commons HTTP 오류",
    "COMMONS_INVALID_RESPONSE": "Commons 응답 형식 오류",
    "COMMONS_INVALID_CONTENT_TYPE": "Commons JSON 형식 아님",
    "COMMONS_RESPONSE_TOO_LARGE": "Commons 응답 크기 초과",
    "COMMONS_REQUEST_FAILED": "Commons 네트워크/TLS/시간 초과",
    "MODE_UNSUPPORTED": "해당 검색 모드 제외",
    "PROVIDER_FAILED": "제공처 오류(원인 미확인)",
}


def safe_source_page(candidate) -> str:
    try:
        parsed = urlsplit(candidate.source_url)
        if (parsed.scheme != "https" or parsed.query or parsed.fragment
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
            return ""
        host = (parsed.hostname or "").lower()
        if candidate.provider == "Wikimedia Commons":
            if host == "commons.wikimedia.org" and parsed.path.startswith("/wiki/File:"):
                return candidate.source_url
        if candidate.provider == "Pixabay":
            if host in ("pixabay.com", "www.pixabay.com") and parsed.path.startswith("/videos/"):
                return candidate.source_url
    except (ValueError, TypeError, AttributeError):
        pass
    return ""


class _PosterThread(QThread):
    ready = Signal(object, int, str, object)

    def __init__(self, mode, sequence: int, candidate, cache_dir: Path):
        super().__init__()
        self.mode, self.sequence, self.candidate = mode, sequence, candidate
        self.cache_dir = cache_dir

    def run(self):
        try:
            result = asyncio.run(PreviewService(self.cache_dir).poster(
                self.candidate.poster_url, self.candidate.provider))
        except Exception:
            result = PreviewResult(
                None, "PREVIEW_NETWORK", "썸네일 연결 실패: 원본 페이지를 확인하세요.")
        self.ready.emit(self.mode, self.sequence, self.candidate.key, result)


class LiveSearchTabsWidget(SearchTabsWidget):
    """Search actual official services; render rights and safe clickable sources."""

    def __init__(self, coordinator, pixabay_adapter, parent=None):
        super().__init__(coordinator, parent)
        self.pixabay_adapter = pixabay_adapter
        self._poster_workers: list[_PosterThread] = []
        self._cache_dir = (
            Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".cache"))
            / "NatureVideoStudio_V2" / "posters"
        )

        layout = self.layout()
        header = QLabel(
            "실제 API 검색 · Commons(장편) / Pixabay(장편·클립, 키 필요) · "
            "실파일·촬영 원본·상업적 이용은 미검증"
        )
        header.setObjectName("realProviderNotice")
        header.setWordWrap(True)
        layout.insertWidget(0, header)

        key_row = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setObjectName("pixabaySessionKey")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText(
            "기존 Pixabay 키 자동 확인 실패 시 API 키 입력 (이번 실행에서만)"
        )
        key_row.addWidget(self.key_input, 1)
        apply_key = QPushButton("Pixabay 키 적용")
        apply_key.setObjectName("applyPixabaySessionKey")
        apply_key.clicked.connect(self._apply_key)
        key_row.addWidget(apply_key)
        layout.insertLayout(1, key_row)

        self.key_status = QLabel(
            "보안 저장소는 검색 시 읽기 전용으로 확인합니다. "
            "여기에 입력한 키는 메모리에만 유지되고 저장되지 않습니다."
        )
        self.key_status.setObjectName("pixabayKeyStatus")
        self.key_status.setWordWrap(True)
        layout.insertWidget(2, self.key_status)

        for mode, pane in self.panes.items():
            if mode == SearchMode.LONG_ORIGINAL:
                pane.provider_policy.setText(
                    "실제 장편 검색: Commons + Pixabay(키 필요). "
                    "180초 이상 공급처 메타데이터만 표시하며 3분 미만 자동 대체 없음. "
                    "Pexels는 장편 제공처에서 제외합니다.")
            else:
                pane.provider_policy.setText(
                    "실제 짧은 영상 검색: Pixabay(키 필요, 5~120초만). "
                    "Pexels는 정책상 짧은 클립 공급처지만 현재 미연결.")
            pane.provider_details = QLabel("제공처 검색 전 · 검색 버튼을 눌러주세요.")
            pane.provider_details.setObjectName(
                "longProviderDetails" if mode == SearchMode.LONG_ORIGINAL
                else "shortProviderDetails"
            )
            pane.provider_details.setWordWrap(True)
            pane.layout().insertWidget(pane.layout().count() - 1, pane.provider_details)

            row = QHBoxLayout()
            pane.poster = QLabel("검색 후 결과를 선택하면\n썸네일을 가져옵니다.")
            pane.poster.setObjectName(
                "longPoster" if mode == SearchMode.LONG_ORIGINAL else "shortPoster"
            )
            pane.poster.setFixedSize(240, 135)
            pane.poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pane.poster.setWordWrap(True)
            row.addWidget(pane.poster)

            right = QVBoxLayout()
            pane.detail = QLabel("결과를 선택하여 제작자·라이선스·원본 페이지 확인")
            pane.detail.setWordWrap(True)
            pane.detail.setObjectName(
                "longResultDetail" if mode == SearchMode.LONG_ORIGINAL else "shortResultDetail"
            )
            right.addWidget(pane.detail)
            buttons = QHBoxLayout()
            pane.source_link = QPushButton("공식 원본 페이지 열기")
            pane.source_link.setObjectName(
                "longOpenSource" if mode == SearchMode.LONG_ORIGINAL else "shortOpenSource"
            )
            pane.source_link.setEnabled(False)
            pane.source_link.clicked.connect(
                lambda checked=False, target=mode: self._open_source(target)
            )
            buttons.addWidget(pane.source_link)
            pane.retry_image = QPushButton("썸네일 재시도")
            pane.retry_image.setEnabled(False)
            pane.retry_image.clicked.connect(
                lambda checked=False, target=mode: self._load_poster(target)
            )
            buttons.addWidget(pane.retry_image)
            right.addLayout(buttons)
            right.addWidget(QLabel(
                "실제 동영상 재생·다운로드 기능은 아직 구현되지 않았습니다."
            ))
            row.addLayout(right, 1)
            pane.layout().addLayout(row)
            pane.results.itemSelectionChanged.connect(
                lambda target=mode: self._selected(target)
            )

    def _apply_key(self):
        # Do not print, log, persist, or reuse the entered key outside this run.
        if self.pixabay_adapter.set_session_key(self.key_input.text()):
            self.key_input.clear()
            self.key_status.setText(
                "Pixabay 키를 이번 실행 메모리에만 적용했습니다. "
                "Windows 기존 키와 V1 자료는 변경하지 않았습니다."
            )
        else:
            self.key_status.setText("키는 10~512자여야 합니다. 입력을 저장하지 않았습니다.")

    def _candidate(self, mode):
        pane = self.panes[mode]
        row = pane.results.currentRow()
        lane = self.session.lane(mode)
        return lane.results[row] if 0 <= row < len(lane.results) else None

    def _selected(self, mode):
        pane = self.panes[mode]
        candidate = self._candidate(mode)
        pane.poster.clear()
        pane.source_link.setEnabled(bool(candidate and safe_source_page(candidate)))
        pane.retry_image.setEnabled(bool(candidate and candidate.poster_url))
        if candidate is None:
            pane.poster.setText("검색 결과를 선택하세요.")
            pane.detail.setText("결과를 선택하여 제작자·라이선스·원본 페이지 확인")
            return
        decision = license_triage(candidate.license_url, candidate.provider)
        w, h = candidate.max_resolution
        pane.detail.setText(
            f"{candidate.title}\n"
            f"제작자: {candidate.creator or '미확인'} · "
            f"길이: {_time_text(candidate.duration_seconds)} · "
            f"제공처 메타데이터 {w}×{h}\n"
            f"라이선스: {candidate.license_url or '미확인'}\n"
            f"권리 상태: {decision.status.value} — {decision.reason}\n"
            f"{candidate.notes}"
        )
        self._load_poster(mode)

    def _load_poster(self, mode):
        pane = self.panes[mode]
        candidate = self._candidate(mode)
        if candidate is None or not candidate.poster_url:
            pane.poster.setText("썸네일 주소 미제공\n공식 원본 페이지에서 확인")
            return
        pane.poster.setText("실제 썸네일 불러오는 중…")
        worker = _PosterThread(
            mode, self.session.lane(mode).sequence, candidate, self._cache_dir
        )
        self._poster_workers.append(worker)
        worker.ready.connect(self._poster_ready)
        worker.finished.connect(lambda w=worker: self._retire_poster(w))
        worker.start()

    def _poster_ready(self, mode, sequence, key, result):
        if self.session.lane(mode).sequence != sequence:
            return
        candidate = self._candidate(mode)
        if candidate is None or candidate.key != key:
            return
        pane = self.panes[mode]
        if result.path:
            image = QPixmap(str(result.path))
            if not image.isNull():
                pane.poster.setPixmap(image.scaled(
                    pane.poster.size(), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                return
            pane.poster.setText("PREVIEW_DECODE: 이미지 해석 실패")
        else:
            pane.poster.setText(f"{result.code}: {result.message}")

    def _retire_poster(self, worker):
        if worker in self._poster_workers:
            self._poster_workers.remove(worker)
        worker.deleteLater()

    def _open_source(self, mode):
        candidate = self._candidate(mode)
        url = safe_source_page(candidate) if candidate else ""
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _complete(self, ticket, outcome):
        super()._complete(ticket, outcome)
        # A new search token protects the status text from stale worker replies.
        if self.session.lane(ticket.mode).sequence != ticket.sequence:
            return
        pane = self.panes[ticket.mode]
        pane.provider_details.setText(" / ".join(
            p.provider + ": " + STATUS_MESSAGES.get(p.code, "상태 확인 불가")
            + (f" (후보 {p.returned_count}건)" if p.code == "OK" else "")
            for p in outcome.providers
        ) or "검색 공급처 없음")

    def _failed(self, ticket):
        super()._failed(ticket)
        if self.session.lane(ticket.mode).sequence == ticket.sequence:
            self.panes[ticket.mode].provider_details.setText(
                "검색 처리 실패: 제공처 결과를 확인할 수 없습니다.")
