from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
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

        self._build_ui()
        self._connect_events()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(22, 22, 22, 22)
        root_layout.setSpacing(18)

        title = QLabel(text("upload_title"))
        title.setObjectName("pageTitle")

        description = QLabel(text("upload_description"))
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        self.select_button = QPushButton(text("select_video"))
        self.select_button.setObjectName("primaryButton")
        self.select_button.setMinimumHeight(44)

        information_card = self._build_information_card()

        root_layout.addWidget(title)
        root_layout.addWidget(description)
        root_layout.addWidget(self.select_button)
        root_layout.addWidget(information_card, 1)

    def _build_information_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(15)

        title = QLabel(text("video_information"))
        title.setObjectName("panelTitle")

        layout.addWidget(title)

        self.name_value = self._add_information_row(
            layout,
            text("video_name"),
        )
        self.resolution_value = self._add_information_row(
            layout,
            text("video_resolution"),
        )
        self.fps_value = self._add_information_row(
            layout,
            text("video_fps"),
        )
        self.duration_value = self._add_information_row(
            layout,
            text("video_duration"),
        )
        self.size_value = self._add_information_row(
            layout,
            text("video_size"),
        )
        self.path_value = self._add_information_row(
            layout,
            text("video_path"),
            wrap=True,
        )

        layout.addStretch()

        return card

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

    def _connect_events(self) -> None:
        self.select_button.clicked.connect(self._choose_video)

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

        self._load_video_information(video_info)

    def _load_video_information(self, video_info: VideoInfo) -> None:
        self._video_info = video_info

        self.name_value.setText(video_info.file_name)
        self.resolution_value.setText(video_info.resolution_text)
        self.fps_value.setText(video_info.fps_text)
        self.duration_value.setText(video_info.duration_text)
        self.size_value.setText(video_info.file_size_text)
        self.path_value.setText(str(video_info.path))

        self.select_button.setText(text("change_video"))

        self.video_selected.emit(video_info)