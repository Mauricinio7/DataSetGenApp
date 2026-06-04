from pathlib import Path

from PySide6.QtCore import QThread, Signal
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
from app.ui.dialogs.model_validation_dialog import ModelValidationDialog
from core.models.model_info import ExecutionBackend, ModelFormat, ModelInfo
from workers.model_validation_worker import ModelValidationWorker


class SelectModelPage(QWidget):

    model_selected = Signal(object)
    model_invalidated = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("contentPage")

        self._model_info: ModelInfo | None = None

        self._validation_thread: QThread | None = None
        self._validation_worker: ModelValidationWorker | None = None
        self._validation_dialog: ModelValidationDialog | None = None

        self._build_ui()
        self._connect_events()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        title = QLabel(text("model_title"))
        title.setObjectName("pageTitle")

        description = QLabel(text("model_description"))
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        self.select_button = QPushButton(text("select_model"))
        self.select_button.setObjectName("primaryButton")
        self.select_button.setMinimumHeight(44)

        self.status_card = self._build_status_card()
        self.information_card = self._build_information_card()
        self.note_card = self._build_note_card()

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.select_button)
        layout.addWidget(self.status_card)
        layout.addWidget(self.information_card, 1)
        layout.addWidget(self.note_card)

    def _build_status_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("modelStatusCard")
        card.setProperty("validationState", "empty")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        status_title = QLabel(text("model_status"))
        status_title.setObjectName("metadataLabel")

        self.status_value = QLabel(text("model_empty"))
        self.status_value.setObjectName("modelStatusValue")
        self.status_value.setWordWrap(True)

        layout.addWidget(status_title)
        layout.addWidget(self.status_value)

        return card

    def _build_information_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(text("model_information"))
        title.setObjectName("panelTitle")

        layout.addWidget(title)

        self.file_value = self._add_information_row(
            layout,
            text("model_file"),
        )

        self.format_value = self._add_information_row(
            layout,
            text("model_format"),
        )

        self.size_value = self._add_information_row(
            layout,
            text("model_size"),
        )

        self.device_value = self._add_information_row(
            layout,
            text("model_device"),
            wrap=True,
        )

        self.path_value = self._add_information_row(
            layout,
            text("model_path"),
            wrap=True,
        )

        layout.addStretch()

        return card

    def _build_note_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("modelNoteCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)

        title = QLabel(text("model_note_title"))
        title.setObjectName("modelNoteTitle")

        note = QLabel(text("model_note"))
        note.setObjectName("modelNoteText")
        note.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(note)

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
        self.select_button.clicked.connect(self._choose_model)

    def _choose_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            text("model_dialog_title"),
            "",
            text("model_filter"),
        )

        if not file_path:
            return

        self._start_validation(Path(file_path))

    def _start_validation(self, model_path: Path) -> None:
        """
        Invalida inmediatamente cualquier modelo anterior y comienza
        la validación del nuevo archivo en segundo plano.
        """

        self._model_info = None

        # Desde este momento ya no se permite continuar usando el modelo previo.
        self.model_invalidated.emit()

        self._clear_model_information()

        self.select_button.setEnabled(False)

        self._set_status(
            text("model_validating"),
            "validating",
        )

        self._validation_dialog = ModelValidationDialog(self)
        self._validation_dialog.show()

        self._validation_thread = QThread(self)
        self._validation_worker = ModelValidationWorker(model_path)

        self._validation_worker.moveToThread(self._validation_thread)

        self._validation_thread.started.connect(
            self._validation_worker.run
        )

        self._validation_worker.validated.connect(
            self._on_model_validated
        )

        self._validation_worker.failed.connect(
            self._on_validation_failed
        )

        self._validation_worker.finished.connect(
            self._validation_thread.quit
        )

        self._validation_worker.finished.connect(
            self._validation_worker.deleteLater
        )

        self._validation_thread.finished.connect(
            self._validation_thread.deleteLater
        )

        self._validation_thread.finished.connect(
            self._clear_validation_references
        )

        self._validation_thread.start()

    def _clear_model_information(self) -> None:
        """Limpia los datos visibles del modelo anteriormente seleccionado."""

        self.file_value.setText(text("not_selected"))
        self.format_value.setText(text("not_selected"))
        self.size_value.setText(text("not_selected"))
        self.device_value.setText(text("not_selected"))
        self.path_value.setText(text("not_selected"))

    def _on_model_validated(self, model_info: ModelInfo) -> None:
        """Actualiza la página cuando el modelo sí pudo ejecutarse."""

        self._close_validation_dialog()

        self._model_info = model_info

        self.file_value.setText(model_info.file_name)

        self.format_value.setText(
            self._format_text(model_info.model_format)
        )

        self.size_value.setText(model_info.file_size_text)

        self.device_value.setText(
            f"{self._backend_text(model_info.execution_backend)} — "
            f"{model_info.device_name}"
        )

        self.path_value.setText(str(model_info.path))

        self.select_button.setText(text("change_model"))
        self.select_button.setEnabled(True)

        self._set_status(
            text("model_valid"),
            "valid",
        )

        self.model_selected.emit(model_info)

    def _on_validation_failed(self, error_message: str) -> None:
        """Mantiene bloqueado el flujo cuando el modelo no es compatible."""

        self._close_validation_dialog()

        self._model_info = None

        self.select_button.setText(text("select_model"))
        self.select_button.setEnabled(True)

        self._set_status(
            text("model_error_message"),
            "invalid",
        )

        QMessageBox.warning(
            self,
            text("model_error_title"),
            f"{text('model_error_message')}\n\n{error_message}",
        )

    def _close_validation_dialog(self) -> None:
        if self._validation_dialog is not None:
            self._validation_dialog.close()
            self._validation_dialog = None

    def _clear_validation_references(self) -> None:
        self._validation_thread = None
        self._validation_worker = None

    def _set_status(self, message: str, state: str) -> None:
        self.status_value.setText(message)
        self.status_card.setProperty("validationState", state)

        self.status_card.style().unpolish(self.status_card)
        self.status_card.style().polish(self.status_card)
        self.status_card.update()

    @staticmethod
    def _format_text(model_format: ModelFormat) -> str:
        formats = {
            ModelFormat.PYTORCH: text("format_pytorch"),
            ModelFormat.ONNX: text("format_onnx"),
            ModelFormat.TENSORRT: text("format_tensorrt"),
        }

        return formats[model_format]

    @staticmethod
    def _backend_text(backend: ExecutionBackend) -> str:
        backends = {
            ExecutionBackend.CPU: text("backend_cpu"),
            ExecutionBackend.MPS: text("backend_mps"),
            ExecutionBackend.CUDA: text("backend_cuda"),
            ExecutionBackend.TENSORRT: text("backend_tensorrt"),
        }

        return backends[backend]