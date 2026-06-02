from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.localization.texts import text


class StepProgressBar(QWidget):
    """Barra horizontal de navegación con pasos tipo chevron."""

    step_requested = Signal(int)

    STEP_HEIGHT = 54
    ARROW_WIDTH = 16
    GAP = 4

    def __init__(self) -> None:
        super().__init__()

        self._step_names = [
            text("step_1"),
            text("step_2"),
            text("step_3"),
            text("step_4"),
            text("step_5"),
            text("step_6"),
        ]

        self._current_step = 0
        self._maximum_unlocked_step = 0
        self._navigation_enabled = True
        self._step_rectangles: list[QRectF] = []

        self.setObjectName("stepProgressBar")
        self.setFixedHeight(self.STEP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_current_step(self, current_step: int) -> None:
        self._current_step = current_step
        self.update()

    def set_unlocked_step(self, maximum_unlocked_step: int) -> None:
        self._maximum_unlocked_step = maximum_unlocked_step
        self.update()

    def set_navigation_enabled(self, enabled: bool) -> None:
        self._navigation_enabled = enabled
        self.update()

    def paintEvent(self, event) -> None:
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        count = len(self._step_names)
        available_width = self.width() - ((count - 1) * self.GAP)
        step_width = available_width / count

        self._step_rectangles.clear()

        for index, step_name in enumerate(self._step_names):
            x = index * (step_width + self.GAP)
            rect = QRectF(x, 0, step_width, self.STEP_HEIGHT)
            self._step_rectangles.append(rect)

            self._paint_step(painter, rect, index, step_name)

    def _paint_step(
        self,
        painter: QPainter,
        rect: QRectF,
        index: int,
        step_name: str,
    ) -> None:
        path = self._create_chevron_path(rect, index)

        background, border, number_color, text_color = self._colors_for_step(index)

        painter.setPen(QPen(border, 1))
        painter.setBrush(background)
        painter.drawPath(path)

        number_font = QFont()
        number_font.setPointSize(10)
        number_font.setWeight(QFont.Weight.DemiBold)

        label_font = QFont()
        label_font.setPointSize(11)
        label_font.setWeight(
            QFont.Weight.DemiBold
            if index == self._current_step
            else QFont.Weight.Medium
        )

        left_padding = 26 if index == 0 else 34

        painter.setFont(number_font)
        painter.setPen(number_color)
        painter.drawText(
            QRectF(
                rect.left() + left_padding,
                rect.top() + 10,
                rect.width() - left_padding - 18,
                14,
            ),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{index + 1:02d}",
        )

        painter.setFont(label_font)
        painter.setPen(text_color)
        painter.drawText(
            QRectF(
                rect.left() + left_padding,
                rect.top() + 27,
                rect.width() - left_padding - 24,
                18,
            ),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            step_name,
        )

    def _create_chevron_path(self, rect: QRectF, index: int) -> QPainterPath:
        arrow = self.ARROW_WIDTH
        path = QPainterPath()

        if index == 0:
            path.moveTo(rect.left() + 10, rect.top())
        else:
            path.moveTo(rect.left() + arrow, rect.top())

        path.lineTo(rect.right() - arrow, rect.top())
        path.lineTo(rect.right(), rect.center().y())
        path.lineTo(rect.right() - arrow, rect.bottom())

        if index == 0:
            path.lineTo(rect.left() + 10, rect.bottom())
            path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - 10)
            path.lineTo(rect.left(), rect.top() + 10)
            path.quadTo(rect.left(), rect.top(), rect.left() + 10, rect.top())
        else:
            path.lineTo(rect.left() + arrow, rect.bottom())
            path.lineTo(rect.left(), rect.center().y())
            path.lineTo(rect.left() + arrow, rect.top())

        path.closeSubpath()
        return path

    def _colors_for_step(
        self,
        index: int,
    ) -> tuple[QColor, QColor, QColor, QColor]:
        if index < self._current_step:
            return (
                QColor("#183C33"),
                QColor("#2B8062"),
                QColor("#61D39B"),
                QColor("#D4F5E7"),
            )

        if index == self._current_step:
            return (
                QColor("#123E69"),
                QColor("#2384DD"),
                QColor("#6BB8FF"),
                QColor("#F2F7FF"),
            )

        if index <= self._maximum_unlocked_step:
            return (
                QColor("#303844"),
                QColor("#495565"),
                QColor("#AEB9C8"),
                QColor("#E0E6EF"),
            )

        return (
            QColor("#252B33"),
            QColor("#343E4B"),
            QColor("#707B8A"),
            QColor("#929CAA"),
        )

    def mousePressEvent(self, event) -> None:
        if (
            not self._navigation_enabled
            or event.button() != Qt.MouseButton.LeftButton
        ):
            return

        for index, rect in enumerate(self._step_rectangles):
            if rect.contains(QPointF(event.position())):
                if index <= self._maximum_unlocked_step:
                    self.step_requested.emit(index)
                return