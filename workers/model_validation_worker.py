from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from core.models.model_info import ModelInfo
from core.services.model_validation_service import (
    ModelCompatibilityError,
    ModelValidationService,
)


class ModelValidationWorker(QObject):

    validated = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, model_path: Path) -> None:
        super().__init__()

        self._model_path = model_path

    @Slot()
    def run(self) -> None:
        try:
            model_info: ModelInfo = ModelValidationService.validate(
                self._model_path
            )
        except ModelCompatibilityError as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.validated.emit(model_info)
        finally:
            self.finished.emit()