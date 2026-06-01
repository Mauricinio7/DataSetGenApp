from pathlib import Path

from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication) -> None:

    stylesheet_path = Path(__file__).with_name("styles.qss")

    if not stylesheet_path.exists():
        raise FileNotFoundError(
            f"No se encontró la hoja de estilos: {stylesheet_path}"
        )

    stylesheet = stylesheet_path.read_text(encoding="utf-8")
    app.setStyleSheet(stylesheet)