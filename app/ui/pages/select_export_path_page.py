from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.localization.texts import text


class SelectExportPathPage(QWidget):

    export_path_selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("contentPage")

        self._base_directory: Path | None = None

        self._build_ui()
        self._connect_events()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        title = QLabel(text("export_title"))
        title.setObjectName("pageTitle")

        description = QLabel(text("export_description"))
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        self.select_button = QPushButton(text("select_export_path"))
        self.select_button.setObjectName("primaryButton")
        self.select_button.setMinimumHeight(44)

        self.status_card = self._build_status_card()
        self.information_card = self._build_information_card()
        self.structure_card = self._build_structure_card()

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.select_button)
        layout.addWidget(self.status_card)
        layout.addWidget(self.information_card, 1)
        layout.addWidget(self.structure_card)

    def _build_status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("exportStatusCard")
        card.setProperty("exportState", "empty")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        label = QLabel(text("export_status"))
        label.setObjectName("metadataLabel")

        self.status_value = QLabel(text("export_empty"))
        self.status_value.setObjectName("exportStatusValue")
        self.status_value.setWordWrap(True)

        layout.addWidget(label)
        layout.addWidget(self.status_value)

        return card

    def _build_information_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(text("export_information"))
        title.setObjectName("panelTitle")

        layout.addWidget(title)

        self.base_directory_value = self._add_information_row(
            layout,
            text("export_base_directory"),
            wrap=True,
        )

        self.workspace_value = self._add_information_row(
            layout,
            text("export_workspace"),
            wrap=True,
        )

        layout.addStretch()

        return card

    def _build_structure_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("exportStructureCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(7)

        title = QLabel(text("export_structure_title"))
        title.setObjectName("exportStructureTitle")

        structure = QLabel(text("export_structure_preview"))
        structure.setObjectName("exportStructureText")

        layout.addWidget(title)
        layout.addWidget(structure)

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
        self.select_button.clicked.connect(self._choose_export_directory)

    def _choose_export_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            text("export_dialog_title"),
        )

        if not directory:
            return

        base_directory = Path(directory)

        self._base_directory = base_directory

        self.base_directory_value.setText(str(base_directory))
        self.workspace_value.setText(text("export_structure_preview").splitlines()[0])

        self.select_button.setText(text("change_export_path"))

        self._set_status(
            text("export_ready"),
            "selected",
        )

        self.export_path_selected.emit(base_directory)

    def _set_status(self, message: str, state: str) -> None:
        self.status_value.setText(message)
        self.status_card.setProperty("exportState", state)

        self.status_card.style().unpolish(self.status_card)
        self.status_card.style().polish(self.status_card)
        self.status_card.update()