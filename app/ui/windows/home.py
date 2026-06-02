from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.localization.texts import text
from app.ui.pages.placeholder_page import PlaceholderPage
from app.ui.pages.upload_video_page import UploadVideoPage
from app.ui.widgets.status_header import StatusHeader
from app.ui.widgets.step_sidebar import StepSidebar
from app.ui.widgets.workflow_footer import WorkflowFooter


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(text("app_title"))
        self.resize(1380, 820)
        self.setMinimumSize(1120, 700)

        self._current_step = 0
        self._maximum_unlocked_step = 0
        self._video_is_selected = False
        self._analysis_is_running = False

        self._build_ui()
        self._connect_events()
        self._show_step(0)

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("mainContainer")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.header = StatusHeader()
        self.sidebar = StepSidebar()
        self.footer = WorkflowFooter()

        self.pages = QStackedWidget()
        self.pages.setObjectName("workflowPages")

        self.upload_video_page = UploadVideoPage()
        self.select_model_page = PlaceholderPage(
            text("placeholder_model_message")
        )

        self.pages.addWidget(self.upload_video_page)
        self.pages.addWidget(self.select_model_page)

        workspace = QWidget()
        workspace.setObjectName("workspaceContainer")

        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(22, 20, 22, 20)
        workspace_layout.setSpacing(18)

        workspace_layout.addWidget(self.sidebar)
        workspace_layout.addWidget(self.pages, 1)

        root_layout.addWidget(self.header)
        root_layout.addWidget(workspace, 1)
        root_layout.addWidget(self.footer)

    def _connect_events(self) -> None:
        self.upload_video_page.video_selected.connect(self._on_video_selected)
        self.sidebar.step_requested.connect(self._request_step)
        self.footer.previous_clicked.connect(self._go_previous_or_cancel)
        self.footer.next_clicked.connect(self._go_next)

    def _on_video_selected(self, video_info: object) -> None:
        del video_info

        self._video_is_selected = True

        if self._current_step == 0:
            self.footer.set_next_enabled(True)

    def _request_step(self, requested_step: int) -> None:
        if self._analysis_is_running:
            return

        if requested_step <= self._maximum_unlocked_step:
            self._show_step(requested_step)

    def _go_next(self) -> None:
        if self._analysis_is_running:
            return

        if self._current_step == 0 and self._video_is_selected:
            self._maximum_unlocked_step = 1
            self.sidebar.set_unlocked_step(self._maximum_unlocked_step)
            self._show_step(1)

    def _go_previous_or_cancel(self) -> None:
        if self._analysis_is_running:
            return

        if self._current_step == 0:
            self.close()
            return

        self._show_step(self._current_step - 1)

    def _show_step(self, step_index: int) -> None:
        self._current_step = step_index
        self.pages.setCurrentIndex(step_index)
        self.sidebar.set_current_step(step_index)

        self.footer.set_step_has_previous(step_index > 0)

        if step_index == 0:
            self.footer.set_next_enabled(self._video_is_selected)
        else:
            self.footer.set_next_enabled(False)