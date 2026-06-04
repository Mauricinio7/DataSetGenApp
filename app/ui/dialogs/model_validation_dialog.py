from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from app.localization.texts import text


class ModelValidationDialog(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setObjectName("modelValidationDialog")
        self.setWindowTitle(text("validation_dialog_title"))
        self.setModal(True)
        self.setFixedWidth(420)

        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        title = QLabel(text("model_validating"))
        title.setObjectName("validationDialogTitle")

        description = QLabel(text("model_validating_description"))
        description.setObjectName("validationDialogDescription")
        description.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("validationProgress")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.progress_bar)