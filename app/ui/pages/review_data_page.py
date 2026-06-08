from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.localization.texts import text
from core.models.dataset_workspace import DatasetWorkspace


class ReviewDataPage(QWidget):

    records_changed = Signal(int)

    CARD_WIDTH = 260
    PREVIEW_HEIGHT = 185
    MIN_GRID_COLUMNS = 1
    GRID_SPACING = 10
    RENDER_BATCH_SIZE = 10
    LOADING_DIALOG_DELAY_MS = 250

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("reviewDataPage")

        self._workspace: DatasetWorkspace | None = None
        self._records: list[dict[str, Path]] = []
        self._cards: list[QFrame] = []

        self._record_count = 0
        self._last_column_count = 0
        self._next_render_index = 0
        self._is_rendering = False

        self._loading_dialog: QDialog | None = None
        self._loading_dialog_timer = QTimer(self)
        self._loading_dialog_timer.setSingleShot(True)
        self._loading_dialog_timer.timeout.connect(
            self._show_loading_dialog
        )

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel(text("review_title"))
        title.setObjectName("pageTitle")

        description = QLabel(text("review_description"))
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        self.empty_label = QLabel(text("review_empty"))
        self.empty_label.setObjectName("reviewEmptyText")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("reviewScrollArea")
        self.scroll_area.setWidgetResizable(True)

        self.grid_container = QWidget()
        self.grid_container.setObjectName("reviewGridContainer")

        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(self.GRID_SPACING)
        self.grid_layout.setVerticalSpacing(self.GRID_SPACING)

        self.scroll_area.setWidget(self.grid_container)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.empty_label, 1)
        layout.addWidget(self.scroll_area, 1)

    def load_workspace(self, workspace: DatasetWorkspace) -> None:
        self._workspace = workspace
        self._records = self._find_records(workspace)
        self._record_count = len(self._records)

        self._clear_grid()
        self._cards.clear()

        self._next_render_index = 0
        self._last_column_count = 0

        self.empty_label.setVisible(self._record_count == 0)
        self.scroll_area.setVisible(self._record_count > 0)

        self.records_changed.emit(self._record_count)

        if self._record_count == 0:
            self._close_loading_dialog()
            return

        self._is_rendering = True
        self._loading_dialog_timer.start(self.LOADING_DIALOG_DELAY_MS)

        QTimer.singleShot(0, self._render_next_batch)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        if not self._cards:
            return

        column_count = self._calculate_column_count()

        if column_count != self._last_column_count:
            self._relayout_cards()

    def _find_records(
        self,
        workspace: DatasetWorkspace,
    ) -> list[dict[str, Path]]:
        records: list[dict[str, Path]] = []

        if not workspace.previews_directory.exists():
            return records

        preview_paths = sorted(
            workspace.previews_directory.glob("*.jpg")
        )

        for preview_path in preview_paths:
            stem = preview_path.stem

            image_path = workspace.images_directory / f"{stem}.jpg"
            label_path = workspace.labels_directory / f"{stem}.txt"

            if not image_path.exists() or not label_path.exists():
                continue

            records.append(
                {
                    "preview": preview_path,
                    "image": image_path,
                    "label": label_path,
                }
            )

        return records

    def _render_next_batch(self) -> None:
        if not self._is_rendering:
            return

        column_count = self._calculate_column_count()
        self._last_column_count = column_count

        end_index = min(
            self._next_render_index + self.RENDER_BATCH_SIZE,
            len(self._records),
        )

        for index in range(self._next_render_index, end_index):
            record = self._records[index]
            card = self._build_record_card(record)

            self._cards.append(card)

            row = index // column_count
            column = index % column_count

            self.grid_layout.addWidget(card, row, column)

        self._next_render_index = end_index

        if self._next_render_index >= len(self._records):
            self._is_rendering = False
            self._loading_dialog_timer.stop()
            self._close_loading_dialog()
            return

        QTimer.singleShot(1, self._render_next_batch)

    def _calculate_column_count(self) -> int:
        available_width = self.scroll_area.viewport().width()

        if available_width <= 0:
            available_width = self.width()

        card_total_width = self.CARD_WIDTH + self.GRID_SPACING

        column_count = max(
            self.MIN_GRID_COLUMNS,
            available_width // card_total_width,
        )

        return int(column_count)

    def _relayout_cards(self) -> None:
        column_count = self._calculate_column_count()
        self._last_column_count = column_count

        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        for index, card in enumerate(self._cards):
            row = index // column_count
            column = index % column_count

            self.grid_layout.addWidget(card, row, column)

        self.grid_layout.setColumnStretch(column_count, 1)

    def _build_record_card(self, record: dict[str, Path]) -> QFrame:
        card = QFrame()
        card.setObjectName("reviewRecordCard")
        card.setFixedWidth(self.CARD_WIDTH)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(7)

        preview_label = QLabel()
        preview_label.setObjectName("reviewPreviewImage")
        preview_label.setFixedHeight(self.PREVIEW_HEIGHT)
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(str(record["preview"]))

        if pixmap.isNull():
            preview_label.setText(text("not_selected"))
        else:
            scaled_pixmap = pixmap.scaled(
                self.CARD_WIDTH - 18,
                self.PREVIEW_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            preview_label.setPixmap(scaled_pixmap)

        name_label = QLabel(record["preview"].stem)
        name_label.setObjectName("reviewRecordName")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)

        delete_button = QPushButton("🗑")
        delete_button.setObjectName("deleteRecordButton")
        delete_button.setToolTip(text("delete_record"))
        delete_button.setMinimumHeight(32)
        delete_button.clicked.connect(
            lambda: self._confirm_delete_record(record, card)
        )

        layout.addWidget(preview_label)
        layout.addWidget(name_label)
        layout.addWidget(delete_button)

        return card

    def _confirm_delete_record(
        self,
        record: dict[str, Path],
        card: QFrame,
    ) -> None:
        response = QMessageBox.warning(
            self,
            text("delete_record_title"),
            text("delete_record_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._delete_record_files(record)
        self._remove_record(record, card)

        self._record_count = len(self._records)

        self.empty_label.setVisible(self._record_count == 0)
        self.scroll_area.setVisible(self._record_count > 0)

        self.records_changed.emit(self._record_count)

    @staticmethod
    def _delete_record_files(record: dict[str, Path]) -> None:
        for key in ("preview", "image", "label"):
            path = record[key]

            if path.exists():
                path.unlink()

    def _remove_record(
        self,
        record: dict[str, Path],
        card: QFrame,
    ) -> None:
        self._records = [
            current_record
            for current_record in self._records
            if current_record["preview"] != record["preview"]
        ]

        if card in self._cards:
            self._cards.remove(card)

        self.grid_layout.removeWidget(card)
        card.setParent(None)
        card.deleteLater()

        self._relayout_cards()

    def _clear_grid(self) -> None:
        self._is_rendering = False

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _show_loading_dialog(self) -> None:
        if not self._is_rendering:
            return

        if self._loading_dialog is not None:
            return

        dialog = QDialog(self)
        dialog.setObjectName("modelValidationDialog")
        dialog.setWindowTitle(text("loading_review_title"))
        dialog.setModal(True)
        dialog.setFixedWidth(430)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        title = QLabel(text("loading_review_title"))
        title.setObjectName("validationDialogTitle")

        message = QLabel(text("loading_review_message"))
        message.setObjectName("validationDialogDescription")
        message.setWordWrap(True)

        progress = QProgressBar()
        progress.setObjectName("validationProgress")
        progress.setRange(0, 0)
        progress.setTextVisible(False)

        layout.addWidget(title)
        layout.addWidget(message)
        layout.addWidget(progress)

        self._loading_dialog = dialog
        self._loading_dialog.show()

    def _close_loading_dialog(self) -> None:
        if self._loading_dialog is not None:
            self._loading_dialog.close()
            self._loading_dialog.deleteLater()
            self._loading_dialog = None