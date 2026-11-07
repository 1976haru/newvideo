"""Native Qt video preview for downloaded local files.

This module is NOT imported by headless core tests. Requires PySide6 Multimedia.
Remote streaming must be handled separately after provider policy verification.
"""
from pathlib import Path

from .playback_diagnostics import classify_playback_failure
from PySide6.QtCore import QUrl, Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget


class LocalVideoPlayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.media = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setMuted(True)
        self.media.setAudioOutput(self.audio)
        self.screen = QVideoWidget(self)
        self.media.setVideoOutput(self.screen)
        self.play_button = QPushButton("재생", self)
        self.mute_button = QPushButton("음소거 해제", self)
        self.seek = QSlider(Qt.Orientation.Horizontal, self)
        self.seek.setRange(0, 0)
        self.message = QLabel("로컬 동영상 선택", self)
        col = QVBoxLayout(self)
        col.addWidget(self.screen)
        row = QHBoxLayout()
        row.addWidget(self.play_button)
        row.addWidget(self.mute_button)
        row.addWidget(self.seek)
        col.addLayout(row)
        col.addWidget(self.message)
        self.play_button.clicked.connect(self.toggle_play)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.seek.sliderMoved.connect(self.media.setPosition)
        self.media.positionChanged.connect(self.seek.setValue)
        self.media.durationChanged.connect(self.seek.setMaximum)
        self.media.errorOccurred.connect(self._error)
        self.media.playbackStateChanged.connect(self._state)

    def open_local(self, filename: str | Path):
        file = Path(filename).expanduser().resolve()
        if not file.is_file() or file.suffix.lower() not in {".mp4", ".mkv", ".mov", ".webm"}:
            self.message.setText("지원되지 않거나 존재하지 않는 로컬 영상")
            return
        self.media.stop()
        self.media.setSource(QUrl.fromLocalFile(str(file)))
        self.message.setText(f"영상 준비: {file.name}")

    def toggle_play(self):
        if self.media.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media.pause()
        else:
            self.media.play()

    def toggle_mute(self):
        is_muted = not self.audio.isMuted()
        self.audio.setMuted(is_muted)
        self.mute_button.setText("음소거 해제" if is_muted else "음소거")

    def _state(self, state):
        self.play_button.setText("일시정지" if state == QMediaPlayer.PlaybackState.PlayingState else "재생")

    def _error(self, error, details):
        if error != QMediaPlayer.Error.NoError:
            # Raw Qt backend error text can include local paths or signed URLs.
            # Display only a stable diagnostic code and generic Korean message.
            diagnosis = classify_playback_failure(details or "")
            self.message.setText(f"영상 재생 오류 [{diagnosis.code}]: {diagnosis.message}")
