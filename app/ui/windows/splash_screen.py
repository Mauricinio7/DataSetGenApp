from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QWidget


class SplashScreen(QWidget):

    SCREEN_WIDTH_RATIO = 0.34
    CORNER_RADIUS_RATIO = 0.035

    def __init__(self, image_path: Path) -> None:
        super().__init__()

        self._pixmap = QPixmap(str(image_path))

        if self._pixmap.isNull():
            raise FileNotFoundError(
                f"No se pudo cargar la imagen del splash: {image_path}"
            )

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        self._configure_size_and_position()

    def _configure_size_and_position(self) -> None:
        screen = QApplication.primaryScreen()

        if screen is None:
            raise RuntimeError("No se pudo detectar la pantalla principal.")

        available_geometry = screen.availableGeometry()

        splash_width = int(
            available_geometry.width() * self.SCREEN_WIDTH_RATIO
        )

        image_ratio = self._pixmap.height() / self._pixmap.width()
        splash_height = int(splash_width * image_ratio)

        self.resize(splash_width, splash_height)

        center_x = (
            available_geometry.x()
            + (available_geometry.width() - splash_width) // 2
        )
        center_y = (
            available_geometry.y()
            + (available_geometry.height() - splash_height) // 2
        )

        self.move(center_x, center_y)

    def paintEvent(self, event) -> None:
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        bounds = QRectF(self.rect())
        corner_radius = self.width() * self.CORNER_RADIUS_RATIO

        rounded_path = QPainterPath()
        rounded_path.addRoundedRect(
            bounds,
            corner_radius,
            corner_radius,
        )

        painter.setClipPath(rounded_path)

        scaled_pixmap = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        image_x = (self.width() - scaled_pixmap.width()) // 2
        image_y = (self.height() - scaled_pixmap.height()) // 2

        painter.drawPixmap(image_x, image_y, scaled_pixmap)