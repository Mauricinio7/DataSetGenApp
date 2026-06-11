from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.localization.texts import text


class FinishPage(QWidget):

    close_app_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("finishPage")

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 42, 42, 42)
        layout.setSpacing(22)

        layout.addStretch()

        card = QFrame()
        card.setObjectName("finishCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(34, 34, 34, 34)
        card_layout.setSpacing(18)

        title = QLabel(text("finish_title"))
        title.setObjectName("finishTitle")

        intro = QLabel(text("finish_dataset_location_intro"))
        intro.setObjectName("finishDescription")
        intro.setWordWrap(True)

        self.dataset_path_label = QLabel("")
        self.dataset_path_label.setObjectName("finishDatasetPath")
        self.dataset_path_label.setWordWrap(True)

        thank_you = QLabel(text("finish_thank_you"))
        thank_you.setObjectName("finishThankYou")
        thank_you.setWordWrap(True)

        self.finish_button = QPushButton(text("finish_app"))
        self.finish_button.setObjectName("primaryButton")
        self.finish_button.setMinimumHeight(42)
        self.finish_button.clicked.connect(
            self.close_app_requested.emit
        )

        card_layout.addWidget(title)
        card_layout.addWidget(intro)
        card_layout.addWidget(self.dataset_path_label)
        card_layout.addSpacing(8)
        card_layout.addWidget(thank_you)
        card_layout.addSpacing(12)
        card_layout.addWidget(self.finish_button)

        layout.addWidget(card)
        layout.addStretch()

    def set_dataset_path(self, dataset_path: Path | str) -> None:
        self.dataset_path_label.setText(str(dataset_path))