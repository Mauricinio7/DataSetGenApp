from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app.localization.texts import text


class WorkflowFooter(QFrame):

    previous_clicked = Signal()
    next_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("workflowFooter")

        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 16, 24, 18)
        root_layout.setSpacing(14)

        progress_header = QHBoxLayout()

        progress_title = QLabel(text("progress_title"))
        progress_title.setObjectName("progressTitle")

        self.progress_status = QLabel(text("progress_waiting"))
        self.progress_status.setObjectName("progressStatus")

        progress_header.addWidget(progress_title)
        progress_header.addStretch()
        progress_header.addWidget(self.progress_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("analysisProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setEnabled(False)

        navigation_layout = QHBoxLayout()

        self.previous_button = QPushButton(text("cancel"))
        self.previous_button.setObjectName("secondaryButton")
        self.previous_button.clicked.connect(self.previous_clicked.emit)

        self.next_button = QPushButton(text("continue"))
        self.next_button.setObjectName("primaryButton")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next_clicked.emit)

        navigation_layout.addWidget(self.previous_button)
        navigation_layout.addStretch()
        navigation_layout.addWidget(self.next_button)

        root_layout.addLayout(progress_header)
        root_layout.addWidget(self.progress_bar)
        root_layout.addLayout(navigation_layout)

    def set_next_enabled(self, enabled: bool) -> None:
        self.next_button.setEnabled(enabled)

    def set_step_has_previous(self, has_previous: bool) -> None:
        self.previous_button.setText(
            text("previous") if has_previous else text("cancel")
        )