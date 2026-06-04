from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QApplication
)

from app.localization.texts import text

from app.ui.widgets.status_header import StatusHeader
from app.ui.widgets.step_sidebar import StepSidebar
from app.ui.widgets.workflow_footer import WorkflowFooter
from app.ui.widgets.video_preview_panel import VideoPreviewPanel

from app.ui.pages.select_model_page import SelectModelPage
from app.ui.pages.upload_video_page import UploadVideoPage
from app.ui.pages.placeholder_page import PlaceholderPage



class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(text("app_title"))
        self._configure_size()

        self._current_step = 0
        self._maximum_unlocked_step = 0
        self._video_is_selected = False
        self._analysis_is_running = False
        self._model_is_selected = False

        self._build_ui()
        self._connect_events()
        self._show_step(0)

    def _configure_size(self) -> None:
        screen = QApplication.primaryScreen()

        if screen is None:
            raise RuntimeError("No se pudo detectar la pantalla principal.")

        available_geometry = screen.availableGeometry()

        self.resize(available_geometry.width(), available_geometry.height())
        self.setMinimumSize(available_geometry.width() * 0.5, available_geometry.height() * 0.75)
        

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("mainContainer")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.header = StatusHeader()
        self.sidebar = StepSidebar()
        self.video_preview = VideoPreviewPanel()
        self.footer = WorkflowFooter()

        self.pages = QStackedWidget()
        self.pages.setObjectName("workflowPages")

        self.upload_video_page = UploadVideoPage()
        self.select_model_page = SelectModelPage()
        self.placeholder_page = PlaceholderPage(
            text("placeholder_model_message")
        )

        self.pages.addWidget(self.upload_video_page)
        self.pages.addWidget(self.select_model_page)
        self.pages.addWidget(self.placeholder_page)

        workspace = QWidget()
        workspace.setObjectName("workspaceContainer")

        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(22, 20, 22, 20)
        workspace_layout.setSpacing(18)

        self.pages.setMinimumWidth(350)
        self.pages.setMaximumWidth(390)

        workspace_layout.addWidget(self.sidebar)
        workspace_layout.addWidget(self.video_preview, 1)
        workspace_layout.addWidget(self.pages)

        root_layout.addWidget(self.header)
        root_layout.addWidget(workspace, 1)
        root_layout.addWidget(self.footer)

    def _connect_events(self) -> None:
        self.upload_video_page.video_selected.connect(self._on_video_selected)
        self.select_model_page.model_selected.connect(self._on_model_selected)
        self.select_model_page.model_invalidated.connect(
            self._on_model_invalidated
        )
        self.sidebar.step_requested.connect(self._request_step)
        self.footer.previous_clicked.connect(self._go_previous_or_cancel)
        self.footer.next_clicked.connect(self._go_next)

    def _on_video_selected(self, video_info: object) -> None:
        self._video_is_selected = True

        self.video_preview.load_video(video_info.path)

        if self._current_step == 0:
            self.footer.set_next_enabled(True)

    def _on_model_selected(self, model_info: object) -> None:
        self._model_is_selected = True

        self.header.set_model(model_info.file_name)

        if self._current_step == 1:
            self.footer.set_next_enabled(True)

    def _on_model_invalidated(self) -> None:
        self._model_is_selected = False

        self.header.clear_model()

        self._maximum_unlocked_step = min(
            self._maximum_unlocked_step,
            1,
        )

        self.sidebar.set_unlocked_step(self._maximum_unlocked_step)

        self._show_step(1)

    def _request_step(self, requested_step: int) -> None:
        if self._analysis_is_running:
            return

        if requested_step <= self._maximum_unlocked_step:
            self._show_step(requested_step)

    def _go_next(self) -> None:
        if self._analysis_is_running:
            return

        if self._current_step == 0 and self._video_is_selected:
            self._maximum_unlocked_step = max(self._maximum_unlocked_step, 1)
            self.sidebar.set_unlocked_step(self._maximum_unlocked_step)
            self._show_step(1)
            return

        if self._current_step == 1 and self._model_is_selected:
            self._maximum_unlocked_step = max(self._maximum_unlocked_step, 2)
            self.sidebar.set_unlocked_step(self._maximum_unlocked_step)
            self._show_step(2)

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
        elif step_index == 1:
            self.footer.set_next_enabled(self._model_is_selected)
        else:
            self.footer.set_next_enabled(False)