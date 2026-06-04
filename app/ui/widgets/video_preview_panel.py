from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
)

from app.localization.texts import text


class VideoPreviewPanel(QFrame):

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("videoPreviewPanel")

        self._build_player()
        self._build_ui()
        self._connect_player_events()

    def _build_player(self) -> None:
        self.audio_output = QAudioOutput(self)
        self.audio_output.setMuted(True)

        self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output)

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("videoPreview")
        self.media_player.setVideoOutput(self.video_widget)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title = QLabel(text("preview_title"))
        title.setObjectName("panelTitle")

        self.empty_preview_label = QLabel(text("preview_empty"))
        self.empty_preview_label.setObjectName("emptyVideoPreview")
        self.empty_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.video_widget.hide()

        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.play_button = QPushButton()
        self.play_button.setObjectName("playButton")
        self.play_button.setFixedSize(44, 44)
        self.play_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self.play_button.setEnabled(False)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setObjectName("videoProgress")
        self.position_slider.setRange(0, 0)
        self.position_slider.setEnabled(False)

        self.time_label = QLabel(text("time_empty"))
        self.time_label.setObjectName("timeLabel")

        controls.addWidget(self.play_button)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.time_label)

        layout.addWidget(title)
        layout.addWidget(self.empty_preview_label, 1)
        layout.addWidget(self.video_widget, 1)
        layout.addLayout(controls)

    def _connect_player_events(self) -> None:
        self.play_button.clicked.connect(self._toggle_playback)
        self.position_slider.sliderMoved.connect(self.media_player.setPosition)

        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.playbackStateChanged.connect(
            self._on_playback_state_changed
        )

    def load_video(self, video_path: Path) -> None:
        """Carga un video seleccionado y muestra su primer frame."""

        self.media_player.stop()
        self.media_player.setSource(QUrl.fromLocalFile(str(video_path)))

        self.empty_preview_label.hide()
        self.video_widget.show()

        self.play_button.setEnabled(True)
        self.position_slider.setEnabled(True)

        self.media_player.play()
        QTimer.singleShot(120, self.media_player.pause)

    def _toggle_playback(self) -> None:
        if (
            self.media_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.media_player.pause()
            return

        self.media_player.play()

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.position_slider.setRange(0, duration_ms)
        self._update_time_label(self.media_player.position(), duration_ms)

    def _on_position_changed(self, position_ms: int) -> None:
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position_ms)

        self._update_time_label(position_ms, self.media_player.duration())

    def _on_playback_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if state == QMediaPlayer.PlaybackState.PlayingState
            else QStyle.StandardPixmap.SP_MediaPlay
        )

        self.play_button.setIcon(self.style().standardIcon(icon))

    def _update_time_label(self, position_ms: int, duration_ms: int) -> None:
        position = self._format_milliseconds(position_ms)
        duration = self._format_milliseconds(duration_ms)
        self.time_label.setText(f"{position} / {duration}")

    @staticmethod
    def _format_milliseconds(milliseconds: int) -> str:
        total_seconds = max(0, milliseconds // 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return f"{minutes:02d}:{seconds:02d}"