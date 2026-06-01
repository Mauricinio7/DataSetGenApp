from PySide6.QtWidgets import QMainWindow, QWidget


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("DataSetGenApp")
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)

        self._build_ui()

    def _build_ui(self) -> None:
        empty_page = QWidget()
        empty_page.setObjectName("mainPage")

        self.setCentralWidget(empty_page)