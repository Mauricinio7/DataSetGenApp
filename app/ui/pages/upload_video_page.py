from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.localization.texts import text
from core.models.video_info import VideoInfo
from core.services.video_metadata_service import VideoMetadataService


class UploadVideoPage(QWidget):

    video_selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("contentPage")

        self._video_info: VideoInfo | None = None
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
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 26, 28, 26)
        root_layout.setSpacing(18)

        page_header = QHBoxLayout()

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        title = QLabel(text("upload_title"))
        title.setObjectName("pageTitle")

        description = QLabel(text("upload_description"))
        description.setObjectName("pageDescription")

        text_layout.addWidget(title)
        text_layout.addWidget(description)

        self.select_button = QPushButton(text("select_video"))
        self.select_button.setObjectName("primaryButton")
        self.select_button.clicked.connect(self._choose_video)

        page_header.addWidget(text_container)
        page_header.addStretch()
        page_header.addWidget(self.select_button)

        central_layout = QHBoxLayout()
        central_layout.setSpacing(18)

        preview_card = QFrame()
        preview_card.setObjectName("panelCard")

        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 14, 14, 14)
        preview_layout.setSpacing(12)

        self.empty_preview_label = QLabel(text("preview_empty"))
        self.empty_preview_label.setObjectName("emptyVideoPreview")
        self.empty_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        preview_stack = QWidget()
        preview_stack.setObjectName("previewContainer")

        preview_stack_layout = QVBoxLayout(preview_stack)
        preview_stack_layout.setContentsMargins(0, 0, 0, 0)
        preview_stack_layout.addWidget(self.video_widget)

        self.video_widget.hide()
        preview_layout.addWidget(self.empty_preview_label, 1)
        preview_layout.addWidget(preview_stack, 1)

        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.play_button = QPushButton()
        self.play_button.setObjectName("playButton")
        self.play_button.setFixedSize(44, 44)
        self.play_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self._toggle_playback)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setObjectName("videoProgress")
        self.position_slider.setRange(0, 0)
        self.position_slider.setEnabled(False)
        self.position_slider.sliderMoved.connect(self.media_player.setPosition)

        self.time_label = QLabel(text("time_empty"))
        self.time_label.setObjectName("timeLabel")

        controls.addWidget(self.play_button)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.time_label)

        preview_layout.addLayout(controls)

        information_card = QFrame()
        information_card.setObjectName("panelCard")
        information_card.setMinimumWidth(286)
        information_card.setMaximumWidth(330)

        information_layout = QVBoxLayout(information_card)
        information_layout.setContentsMargins(20, 20, 20, 20)
        information_layout.setSpacing(16)

        information_title = QLabel(text("video_information"))
        information_title.setObjectName("panelTitle")
        information_layout.addWidget(information_title)

        self.name_value = self._add_information_row(
            information_layout, text("video_name")
        )
        self.resolution_value = self._add_information_row(
            information_layout, text("video_resolution")
        )
        self.fps_value = self._add_information_row(
            information_layout, text("video_fps")
        )
        self.duration_value = self._add_information_row(
            information_layout, text("video_duration")
        )
        self.size_value = self._add_information_row(
            information_layout, text("video_size")
        )
        self.path_value = self._add_information_row(
            information_layout, text("video_path"), wrap=True
        )

        information_layout.addStretch()

        central_layout.addWidget(preview_card, 1)
        central_layout.addWidget(information_card)

        root_layout.addLayout(page_header)
        root_layout.addLayout(central_layout, 1)

    @staticmethod
    def _add_information_row(
        layout: QVBoxLayout,
        label_text: str,
        wrap: bool = False,
    ) -> QLabel:
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        label = QLabel(label_text)
        label.setObjectName("metadataLabel")

        value = QLabel(text("not_selected"))
        value.setObjectName("metadataValue")
        value.setWordWrap(wrap)

        container_layout.addWidget(label)
        container_layout.addWidget(value)

        layout.addWidget(container)

        return value

    def _connect_player_events(self) -> None:
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.playbackStateChanged.connect(
            self._on_playback_state_changed
        )

    def _choose_video(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            text("video_dialog_title"),
            "",
            text("video_filter"),
        )

        if not file_path:
            return

        try:
            video_info = VideoMetadataService.read(Path(file_path))
        except (ValueError, OSError):
            QMessageBox.warning(
                self,
                text("video_error_title"),
                text("video_error_message"),
            )
            return

        self._load_video(video_info)

    def _load_video(self, video_info: VideoInfo) -> None:
        self._video_info = video_info

        self.name_value.setText(video_info.file_name)
        self.resolution_value.setText(video_info.resolution_text)
        self.fps_value.setText(video_info.fps_text)
        self.duration_value.setText(video_info.duration_text)
        self.size_value.setText(video_info.file_size_text)
        self.path_value.setText(str(video_info.path))

        self.select_button.setText(text("change_video"))

        self.empty_preview_label.hide()
        self.video_widget.show()

        self.play_button.setEnabled(True)
        self.position_slider.setEnabled(True)

        self.media_player.setSource(QUrl.fromLocalFile(str(video_info.path)))

        self.media_player.play()
        QTimer.singleShot(100, self.media_player.pause)

        self.video_selected.emit(video_info)

    def _toggle_playback(self) -> None:
        if (
            self.media_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.media_player.pause()
        else:
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
        standard_icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if state == QMediaPlayer.PlaybackState.PlayingState
            else QStyle.StandardPixmap.SP_MediaPlay
        )

        self.play_button.setIcon(
            self.style().standardIcon(standard_icon)
        )

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