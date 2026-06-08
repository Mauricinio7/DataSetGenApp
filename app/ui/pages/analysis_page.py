from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.localization.texts import text


class AnalysisPage(QWidget):
    """Cuarto paso del flujo: ejecución y monitoreo del análisis."""

    start_requested = Signal()
    pause_requested = Signal()
    resume_requested = Signal()
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("contentPage")

        self._is_running = False
        self._is_paused = False

        self._build_ui()
        self._connect_events()
        self.set_ready_state()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel(text("analysis_title"))
        title.setObjectName("pageTitle")

        self.warning_card = self._build_warning_card()
        self.metrics_card = self._build_metrics_card()
        self.actions_card = self._build_actions_card()

        layout.addWidget(title)

        layout.addWidget(self.warning_card)
        layout.addWidget(self.metrics_card, 1)
        layout.addWidget(self.actions_card)

    def _build_warning_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("analysisWarningCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(0)

        warning = QLabel(text("analysis_warning_text_short"))
        warning.setObjectName("analysisWarningText")
        warning.setWordWrap(True)

        layout.addWidget(warning)

        return card

    def _build_metrics_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("analysisMetricsCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self.video_fps_value = self._add_metric_row(
            layout,
            text("analysis_video_fps"),
        )

        self.target_fps_value = self._add_metric_row(
            layout,
            text("analysis_target_fps"),
        )

        self.total_frames_value = self._add_metric_row(
            layout,
            text("analysis_total_frames"),
        )

        self.analyzed_frames_value = self._add_metric_row(
            layout,
            text("analysis_analyzed_frames"),
        )

        self.remaining_frames_value = self._add_metric_row(
            layout,
            text("analysis_remaining_frames"),
        )

        self.processed_video_time_value = self._add_metric_row(
            layout,
            text("analysis_processed_video_time"),
        )

        self.estimated_time_value = self._add_metric_row(
            layout,
            text("analysis_estimated_time"),
        )

        self.processing_rate_value = self._add_metric_row(
            layout,
            text("analysis_processing_rate"),
        )

        self.detections_value = self._add_metric_row(
            layout,
            text("analysis_detections"),
        )

        layout.addStretch()

        return card

    def _build_actions_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("analysisActionsCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.start_button = QPushButton(text("start_analysis"))
        self.start_button.setObjectName("primaryButton")
        self.start_button.setMinimumHeight(40)

        self.pause_button = QPushButton(text("pause_analysis"))
        self.pause_button.setObjectName("secondaryButton")
        self.pause_button.setMinimumHeight(40)

        self.cancel_button = QPushButton(text("cancel_analysis"))
        self.cancel_button.setObjectName("dangerButton")
        self.cancel_button.setMinimumHeight(40)

        layout.addWidget(self.start_button)
        layout.addWidget(self.pause_button)
        layout.addWidget(self.cancel_button)

        return card

    @staticmethod
    def _add_metric_row(
        layout: QVBoxLayout,
        label_text: str,
    ) -> QLabel:
        row = QFrame()
        row.setObjectName("analysisMetricRow")
        row.setMinimumHeight(32)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 5, 10, 5)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("analysisMetricLabel")

        value = QLabel(text("not_selected"))
        value.setObjectName("analysisMetricValue")
        value.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        row_layout.addWidget(label, 1)
        row_layout.addWidget(value, 1)

        layout.addWidget(row)

        return value

    def _connect_events(self) -> None:
        self.start_button.clicked.connect(self.start_requested.emit)
        self.pause_button.clicked.connect(self._toggle_pause)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)

    def set_ready_state(self) -> None:
        self._is_running = False
        self._is_paused = False

        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.pause_button.setText(text("pause_analysis"))

    def set_running_state(self) -> None:
        self._is_running = True
        self._is_paused = False

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.pause_button.setText(text("pause_analysis"))

    def set_paused_state(self) -> None:
        self._is_running = True
        self._is_paused = True

        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.pause_button.setText(text("resume_analysis"))

    def set_cancelled_state(self) -> None:
        self._is_running = False
        self._is_paused = False

        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.pause_button.setText(text("pause_analysis"))

    def set_finished_state(self) -> None:
        self._is_running = False
        self._is_paused = False

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.pause_button.setText(text("pause_analysis"))

    def set_initial_video_metrics(
        self,
        video_fps: str,
        target_fps: str,
        total_frames: str,
    ) -> None:
        self.video_fps_value.setText(video_fps)
        self.target_fps_value.setText(target_fps)
        self.total_frames_value.setText(total_frames)
        self.analyzed_frames_value.setText("0")
        self.remaining_frames_value.setText(total_frames)
        self.processed_video_time_value.setText("00:00")
        self.estimated_time_value.setText("Calculando...")
        self.processing_rate_value.setText("0.00 FPS")
        self.detections_value.setText("0")

    def update_progress_metrics(
        self,
        analyzed_frames: int,
        total_frames: int,
        remaining_frames: int,
        processed_video_time: str,
        estimated_time: str,
        processing_rate_fps: float,
        detections: int,
    ) -> None:
        self.analyzed_frames_value.setText(
            f"{analyzed_frames} / {total_frames}"
        )
        self.remaining_frames_value.setText(str(remaining_frames))
        self.processed_video_time_value.setText(processed_video_time)
        self.estimated_time_value.setText(estimated_time)
        self.processing_rate_value.setText(
            f"{processing_rate_fps:.2f} FPS"
        )
        self.detections_value.setText(str(detections))

    def _toggle_pause(self) -> None:
        if not self._is_running:
            return

        if self._is_paused:
            self.resume_requested.emit()
            return

        self.pause_requested.emit()