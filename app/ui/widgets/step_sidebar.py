from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.localization.texts import text


class StepItem(QPushButton):
    """Elemento visual e interactivo para un paso del flujo."""

    def __init__(self, step_number: int, step_label: str) -> None:
        super().__init__()

        self._step_number = step_number
        self._step_label = step_label

        self.setObjectName("stepItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(64)
        self.setCheckable(False)

        self._build_ui()

    def _build_ui(self) -> None:
        self.setText(f"{self._step_number:02d}   {self._step_label}")

    def set_state(self, state: str) -> None:
        """
        Estados permitidos:
        - active
        - completed
        - available
        - pending
        - locked
        """
        self.setProperty("stepState", state)

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class StepSidebar(QFrame):
    """Navegación vertical del flujo de generación del dataset."""

    step_requested = Signal(int)

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("stepSidebar")

        self._current_step = 0
        self._maximum_unlocked_step = 0
        self._navigation_enabled = True
        self._step_buttons: list[StepItem] = []

        self._build_ui()
        self._refresh_states()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(10)

        header = QLabel("PROCESO")
        header.setObjectName("sidebarHeader")
        layout.addWidget(header)
        layout.addSpacing(8)

        step_names = [
            text("step_1"),
            text("step_2"),
            text("step_3"),
            text("step_4"),
            text("step_5"),
            text("step_6"),
        ]

        for index, step_name in enumerate(step_names):
            button = StepItem(index + 1, step_name)
            button.clicked.connect(
                lambda checked=False, target=index: self._request_step(target)
            )

            self._step_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()

    def _request_step(self, requested_step: int) -> None:
        if not self._navigation_enabled:
            return

        if requested_step <= self._maximum_unlocked_step:
            self.step_requested.emit(requested_step)

    def set_current_step(self, current_step: int) -> None:
        self._current_step = current_step
        self._refresh_states()

    def set_unlocked_step(self, maximum_unlocked_step: int) -> None:
        self._maximum_unlocked_step = maximum_unlocked_step
        self._refresh_states()

    def set_navigation_enabled(self, enabled: bool) -> None:
        self._navigation_enabled = enabled
        self._refresh_states()

    def _refresh_states(self) -> None:
        for index, button in enumerate(self._step_buttons):
            if index == self._current_step:
                state = "active"
                enabled = self._navigation_enabled
            elif index < self._current_step:
                state = "completed"
                enabled = self._navigation_enabled
            elif index <= self._maximum_unlocked_step:
                state = "available"
                enabled = self._navigation_enabled
            else:
                state = "pending"
                enabled = False

            button.set_state(state)
            button.setEnabled(enabled)