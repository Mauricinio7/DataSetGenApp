from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.localization.texts import text


class PlaceholderPage(QWidget):

    def __init__(self, message: str) -> None:
        super().__init__()
        self.setObjectName("contentPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 44, 44, 44)
        layout.setSpacing(12)

        title = QLabel(text("placeholder_title"))
        title.setObjectName("pageTitle")

        description = QLabel(message)
        description.setObjectName("pageDescription")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()