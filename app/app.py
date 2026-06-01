import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.styles.theme import apply_theme
from app.ui.windows.home import MainWindow
from app.ui.windows.splash_screen import SplashScreen


class Application:
    
    SPLASH_DURATION_MS = 3000

    def __init__(self) -> None:
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("DataSetGenApp")

        apply_theme(self.qt_app)

        self.main_window = MainWindow()
        self.splash_screen = SplashScreen(self._splash_image_path())

    @staticmethod
    def _splash_image_path() -> Path:
        project_root = Path(__file__).resolve().parent.parent
        return project_root / "assets" / "images" / "splash.png"

    def run(self) -> int:
        self.splash_screen.show()

        QTimer.singleShot(
            self.SPLASH_DURATION_MS,
            self._open_main_window,
        )

        return self.qt_app.exec()

    def _open_main_window(self) -> None:
        self.main_window.show()
        self.splash_screen.close()


def run_app() -> int:
    application = Application()
    return application.run()