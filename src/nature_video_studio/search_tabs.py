"""C024 two independent Qt search tabs; no real provider is silently invented.

The trial GUI is *not* a real media discovery tool until R1 adapters are
connected. An unconnected search click explicitly says "unavailable".
Injected async fake adapters in tests run on a QThread, never the GUI thread.
"""
from __future__ import annotations

import asyncio

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from .models import ResolutionMode, SearchMode
from .search_mode_state import (
    LaneStatus, LONG_DURATION_PRESETS_SECONDS, SORT_LABELS, SORT_OPTIONS,
    SearchModeSession, SearchTicket,
)
from .source_adapter import SearchQuery
from .duration_self_check import run_duration_self_check


class _SearchThread(QThread):
    completed = Signal(object, object)
    failed = Signal(object)

    def __init__(self, coordinator, ticket: SearchTicket):
        super().__init__()
        self.coordinator = coordinator
        self.ticket = ticket

    def run(self):
        try:
            outcome = asyncio.run(self.coordinator.search(
                SearchQuery(self.ticket.text, self.ticket.criteria)))
        except Exception:
            # Never emit exception text: a provider could include secrets.
            self.failed.emit(self.ticket)
        else:
            self.completed.emit(self.ticket, outcome)


def _time_text(duration: float | None) -> str:
    if duration is None:
        return "미확인"
    seconds = round(duration)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class _LanePane(QWidget):
    def __init__(self, mode: SearchMode, session: SearchModeSession):
        super().__init__()
        self.mode = mode
        self.session = session
        prefix = "long" if mode == SearchMode.LONG_ORIGINAL else "short"
        layout = QVBoxLayout(self)
        layout.setSpacing(9)

        hint = QLabel(
            "검증된 원본 180초 이상 · 미확인은 제외 · 클립 자동 대체 없음"
            if mode == SearchMode.LONG_ORIGINAL
            else "검증된 5~120초 클립만 · 원본 장편과 결과/정렬 독립"
        )
        hint.setObjectName(prefix + "ModeHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        query_row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName(prefix + "SearchQuery")
        self.query.setPlaceholderText("예: 조용한 호수와 산 풍경")
        self.query.setClearButtonEnabled(True)
        query_row.addWidget(self.query, 1)
        self.search_button = QPushButton("이 탭 검색")
        self.search_button.setObjectName(prefix + "SearchButton")
        query_row.addWidget(self.search_button)
        layout.addLayout(query_row)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("정렬"))
        self.sort_choice = QComboBox()
        self.sort_choice.setObjectName(prefix + "SortChoice")
        for choice in SORT_OPTIONS[mode]:
            self.sort_choice.addItem(SORT_LABELS[choice], choice)
        filter_row.addWidget(self.sort_choice, 1)

        filter_row.addWidget(QLabel("해상도"))
        self.resolution = QComboBox()
        self.resolution.setObjectName(prefix + "ResolutionChoice")
        for name, value in (
            ("4K 우선", ResolutionMode.FOUR_K_PREFERRED),
            ("4K만", ResolutionMode.FOUR_K_ONLY),
            ("FHD 이상", ResolutionMode.FHD_MINIMUM),
        ):
            self.resolution.addItem(name, value)
        filter_row.addWidget(self.resolution, 1)
        layout.addLayout(filter_row)

        if mode == SearchMode.LONG_ORIGINAL:
            duration_row = QHBoxLayout()
            duration_row.addWidget(QLabel("최소 원본 길이"))
            self.min_duration = QComboBox()
            self.min_duration.setObjectName("longMinDurationPreset")
            for seconds in LONG_DURATION_PRESETS_SECONDS:
                self.min_duration.addItem(f"{seconds // 60}분 이상", seconds)
            duration_row.addWidget(self.min_duration)

            self.max_duration_enabled = QCheckBox("최대 길이 제한")
            self.max_duration_enabled.setObjectName("longMaxDurationEnabled")
            self.max_duration_enabled.setChecked(False)
            duration_row.addWidget(self.max_duration_enabled)

            self.max_duration_minutes = QSpinBox()
            self.max_duration_minutes.setObjectName("longMaxDurationMinutes")
            self.max_duration_minutes.setRange(1, 1440)
            self.max_duration_minutes.setSingleStep(1)
            self.max_duration_minutes.setValue(60)
            self.max_duration_minutes.setSuffix("분")
            self.max_duration_minutes.setEnabled(False)
            duration_row.addWidget(self.max_duration_minutes)
            duration_row.addStretch()
            layout.addLayout(duration_row)

            self.duration_summary = QLabel()
            self.duration_summary.setObjectName("longDurationSummary")
            self.duration_summary.setWordWrap(True)
            layout.addWidget(self.duration_summary)
            self.min_duration.currentIndexChanged.connect(
                self._update_duration_summary)
            self.max_duration_enabled.toggled.connect(
                self.max_duration_minutes.setEnabled)
            self.max_duration_enabled.toggled.connect(
                self._update_duration_summary)
            self.max_duration_minutes.valueChanged.connect(
                self._update_duration_summary)
            self._update_duration_summary()

        count_row = QHBoxLayout()
        self.count = QLabel()
        self.count.setObjectName(prefix + "ResultCount")
        count_row.addWidget(self.count)
        count_row.addStretch()
        if mode == SearchMode.LONG_ORIGINAL:
            self.duration_check_button = QPushButton("C025 180초 규칙 검사")
            self.duration_check_button.setObjectName("longDurationSelfCheck")
            count_row.addWidget(self.duration_check_button)
        self.switch_button = QPushButton(
            "짧은 영상 조합 탭으로 전환"
            if mode == SearchMode.LONG_ORIGINAL else
            "3분 이상 원본 탭으로 전환"
        )
        self.switch_button.setObjectName(prefix + "SwitchMode")
        count_row.addWidget(self.switch_button)
        layout.addLayout(count_row)

        self.status_label = QLabel()
        self.status_label.setObjectName(prefix + "SearchStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.results = QTableWidget(0, 4)
        self.results.setObjectName(prefix + "ResultsTable")
        self.results.setHorizontalHeaderLabels(
            ("제목", "원본/클립 길이", "제공된 해상도", "출처")
        )
        self.results.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.results.setSortingEnabled(False)
        layout.addWidget(self.results, 1)
        self.refresh()

    def _update_duration_summary(self, *_):
        if self.mode != SearchMode.LONG_ORIGINAL:
            return
        minimum_minutes = self.min_duration.currentData() // 60
        if not self.max_duration_enabled.isChecked():
            value = f"선택 조건: {minimum_minutes}분 이상 / 최대 제한 없음"
        else:
            maximum = self.max_duration_minutes.value()
            if maximum < minimum_minutes:
                value = (f"조건 오류: 최대 {maximum}분은 최소 {minimum_minutes}분보다 짧습니다. "
                         "검색 요청을 보내지 않습니다.")
            else:
                value = f"선택 조건: {minimum_minutes}~{maximum}분 (양 끝 포함)"
        self.duration_summary.setText(value + " · 검색 버튼 클릭 시 적용")

    def refresh(self) -> None:
        lane = self.session.lane(self.mode)
        if lane.status == LaneStatus.SEARCHING:
            count_label = "검색 중"
        elif lane.result_count is None:
            count_label = "미검색" if lane.status == LaneStatus.NOT_SEARCHED else "확인 불가"
        else:
            count_label = f"{lane.result_count}건"
        self.count.setText(f"이 탭의 결과: {count_label}")
        self.status_label.setText(lane.status_text)
        self.results.setRowCount(len(lane.results))
        for row, candidate in enumerate(lane.results):
            w, h = candidate.max_resolution
            values = [
                candidate.title,
                _time_text(candidate.duration_seconds),
                f"{w}×{h} (제공처 메타데이터)" if w and h else "미확인",
                candidate.provider,
            ]
            for column, value in enumerate(values):
                self.results.setItem(row, column, QTableWidgetItem(value))


class SearchTabsWidget(QWidget):
    """Top-level tabs, explicit switch, independent controls and worker replies."""

    def __init__(self, coordinator=None, parent=None):
        super().__init__(parent)
        self.coordinator = coordinator  # None until an authorized source adapter exists
        self.session = SearchModeSession()
        self._threads: list[_SearchThread] = []
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("searchModeTabs")
        self.panes = {
            SearchMode.LONG_ORIGINAL: _LanePane(SearchMode.LONG_ORIGINAL, self.session),
            SearchMode.SHORT_COMPOSER: _LanePane(SearchMode.SHORT_COMPOSER, self.session),
        }
        self.tabs.addTab(self.panes[SearchMode.LONG_ORIGINAL], "3분 이상 원본")
        self.tabs.addTab(self.panes[SearchMode.SHORT_COMPOSER], "짧은 영상 조합")
        layout.addWidget(self.tabs)

        for mode, pane in self.panes.items():
            pane.search_button.clicked.connect(
                lambda checked=False, target=mode: self.request_search(target))
            pane.query.returnPressed.connect(
                lambda target=mode: self.request_search(target))
            pane.switch_button.clicked.connect(
                lambda checked=False, target=mode: self.switch_to(
                    SearchMode.SHORT_COMPOSER if target == SearchMode.LONG_ORIGINAL
                    else SearchMode.LONG_ORIGINAL))
            pane.sort_choice.currentIndexChanged.connect(
                lambda index, target=mode: self._change_sort(target))
        self.tabs.currentChanged.connect(self._tab_changed)
        self.panes[SearchMode.LONG_ORIGINAL].duration_check_button.clicked.connect(
            self.show_duration_self_check)

    def show_duration_self_check(self) -> None:
        """Offline synthetic cases only; this never calls providers or changes counts."""
        cases = run_duration_self_check()
        lines = [
            ("PASS" if c.passed else "FAIL") + " · " + c.label + " → " +
            ("장편 포함" if c.accepted else "장편 제외")
            for c in cases
        ]
        lines.insert(0, "테스트용 합성 데이터 검사입니다. 실제 제공처 검색 결과가 아닙니다.")
        lines.insert(1, "")
        lines.append("")
        lines.append(f"판정: {sum(c.passed for c in cases)}/{len(cases)} PASS")
        message = "\n".join(lines)
        if all(c.passed for c in cases):
            QMessageBox.information(self, "C025 180초 기준 자가검사", message)
        else:
            QMessageBox.warning(self, "C025 180초 기준 자가검사 실패", message)

    def _tab_changed(self, index: int) -> None:
        mode = (SearchMode.LONG_ORIGINAL if index == 0 else SearchMode.SHORT_COMPOSER)
        self.session.switch_to(mode)

    def switch_to(self, mode: SearchMode) -> None:
        target = 0 if mode == SearchMode.LONG_ORIGINAL else 1
        self.tabs.setCurrentIndex(target)
        self.session.switch_to(mode)

    def _change_sort(self, mode: SearchMode) -> None:
        pane = self.panes[mode]
        self.session.set_sort(mode, pane.sort_choice.currentData())
        pane.refresh()

    def request_search(self, mode: SearchMode) -> None:
        pane = self.panes[mode]
        try:
            options = {}
            if mode == SearchMode.LONG_ORIGINAL:
                options = {
                    "min_original_duration_seconds": pane.min_duration.currentData(),
                    "max_original_duration_seconds": (
                        pane.max_duration_minutes.value() * 60
                        if pane.max_duration_enabled.isChecked() else None
                    ),
                }
            ticket = self.session.begin_search(
                mode, pane.query.text(), pane.resolution.currentData(), **options)
        except ValueError as exc:
            # Safe, fixed user-facing messages; do not show raw provider data.
            if not pane.query.text().strip():
                pane.status_label.setText("이 탭의 검색어를 입력하세요.")
            else:
                pane.status_label.setText(
                    "길이 조건 오류: 최대 길이는 최소 길이보다 길거나 같아야 합니다.")
            return
        pane.refresh()
        if self.coordinator is None:
            self.session.unavailable(ticket)
            pane.refresh()
            return
        worker = _SearchThread(self.coordinator, ticket)
        self._threads.append(worker)
        worker.completed.connect(self._complete)
        worker.failed.connect(self._failed)
        worker.finished.connect(lambda w=worker: self._retire(w))
        worker.start()

    def _complete(self, ticket, outcome) -> None:
        if self.session.finish_search(ticket, outcome):
            self.panes[ticket.mode].refresh()

    def _failed(self, ticket) -> None:
        if self.session.failed(ticket):
            self.panes[ticket.mode].refresh()

    def _retire(self, worker: _SearchThread) -> None:
        if worker in self._threads:
            self._threads.remove(worker)
        worker.deleteLater()
