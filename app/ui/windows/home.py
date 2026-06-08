from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QApplication,
    QMessageBox,
)

from pathlib import Path

from app.localization.texts import text

from app.ui.widgets.status_header import StatusHeader
from app.ui.widgets.step_sidebar import StepSidebar
from app.ui.widgets.workflow_footer import WorkflowFooter
from app.ui.widgets.video_preview_panel import VideoPreviewPanel

from app.ui.pages.select_model_page import SelectModelPage
from app.ui.pages.upload_video_page import UploadVideoPage
from app.ui.pages.select_export_path_page import SelectExportPathPage
from app.ui.pages.placeholder_page import PlaceholderPage

from core.models.dataset_workspace import DatasetWorkspace
from core.models.model_info import ModelInfo
from core.models.video_info import VideoInfo
from core.services.dataset_workspace_service import (
    DatasetWorkspaceError,
    DatasetWorkspaceService,
)


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(text("app_title"))
        self._configure_size()

        self._current_step = 0
        self._maximum_unlocked_step = 0

        self._video_info: VideoInfo | None = None
        self._model_info: ModelInfo | None = None

        self._video_is_selected = False
        self._model_is_selected = False
        self._analysis_is_running = False
        self._export_base_directory: Path | None = None
        self._dataset_workspace: DatasetWorkspace | None = None

        self._export_path_is_selected = False
        self._workspace_is_created = False
        
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
        self.select_export_path_page = SelectExportPathPage()

        self.analysis_page = PlaceholderPage(
            text("placeholder_analysis_message")
        )

        self.pages.addWidget(self.upload_video_page)
        self.pages.addWidget(self.select_model_page)
        self.pages.addWidget(self.select_export_path_page)
        self.pages.addWidget(self.analysis_page)

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

        self.select_export_path_page.export_path_selected.connect(
            self._on_export_path_selected
        )

        self.sidebar.step_requested.connect(self._request_step)
        self.footer.previous_clicked.connect(self._go_previous_or_cancel)
        self.footer.next_clicked.connect(self._go_next)

    def _on_video_selected(self, video_info: VideoInfo) -> None:
        video_changed = (
            self._video_info is not None
            and self._video_info.path != video_info.path
        )

        self._video_info = video_info
        self._video_is_selected = True

        self.video_preview.load_video(video_info.path)

        if video_changed:
            self._invalidate_created_workspace()

            self._maximum_unlocked_step = min(
                self._maximum_unlocked_step,
                2,
            )
            self.sidebar.set_unlocked_step(self._maximum_unlocked_step)

        if self._current_step == 0:
            self.footer.set_next_enabled(True)

    def _on_model_selected(self, model_info: ModelInfo) -> None:
        self._model_info = model_info
        self._model_is_selected = True

        self.header.set_model(model_info.file_name)

        if self._current_step == 1:
            self.footer.set_next_enabled(True)

    def _on_model_invalidated(self) -> None:
        self._model_is_selected = False
        self._model_info = None

        self.header.clear_model()

        self._export_base_directory = None
        self._export_path_is_selected = False
        self._invalidate_created_workspace()

        self._maximum_unlocked_step = min(
            self._maximum_unlocked_step,
            1,
        )

        self.sidebar.set_unlocked_step(self._maximum_unlocked_step)

        self._show_step(1)

    def _on_export_path_selected(self, base_directory: Path) -> None:
        self._export_base_directory = base_directory
        self._export_path_is_selected = True

        self._invalidate_created_workspace()

        if self._current_step == 2:
            self.footer.set_next_enabled(True)

    def _invalidate_created_workspace(self) -> None:
        self._dataset_workspace = None
        self._workspace_is_created = False

        self.header.clear_export_path()

        self._maximum_unlocked_step = min(
            self._maximum_unlocked_step,
            2,
        )

        self.sidebar.set_unlocked_step(self._maximum_unlocked_step)

    def _request_step(self, requested_step: int) -> None:
        if self._analysis_is_running:
            return

        if requested_step <= self._maximum_unlocked_step:
            self._show_step(requested_step)

    def _go_next(self) -> None:
        if self._analysis_is_running:
            return

        if self._current_step == 0 and self._video_is_selected:
            self._maximum_unlocked_step = max(
                self._maximum_unlocked_step,
                1,
            )
            self.sidebar.set_unlocked_step(self._maximum_unlocked_step)
            self._show_step(1)
            return

        if self._current_step == 1 and self._model_is_selected:
            self._maximum_unlocked_step = max(
                self._maximum_unlocked_step,
                2,
            )
            self.sidebar.set_unlocked_step(self._maximum_unlocked_step)
            self._show_step(2)
            return

        if self._current_step == 2 and self._export_path_is_selected:
            if (
                self._workspace_is_created
                and self._dataset_workspace is not None
            ):
                self._maximum_unlocked_step = max(
                    self._maximum_unlocked_step,
                    3,
                )
                self.sidebar.set_unlocked_step(self._maximum_unlocked_step)
                self._show_step(3)
                return

            self._create_dataset_workspace()

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
        elif step_index == 2:
            self.footer.set_next_enabled(self._export_path_is_selected)
        else:
            self.footer.set_next_enabled(False)

    def _create_dataset_workspace(self) -> None:
        if (
            self._export_base_directory is None
            or self._video_info is None
            or self._model_info is None
        ):
            QMessageBox.warning(
                self,
                text("export_error_title"),
                text("export_error_message"),
            )
            return

        try:
            workspace = DatasetWorkspaceService.create(
                base_directory=self._export_base_directory,
                video_info=self._video_info,
                model_info=self._model_info,
            )
        except DatasetWorkspaceError as error:
            QMessageBox.warning(
                self,
                text("export_error_title"),
                f"{text('export_error_message')}\n\n{error}",
            )
            return

        self._dataset_workspace = workspace
        self._workspace_is_created = True

        self.header.set_export_path(
            str(workspace.root_directory)
        )

        self._maximum_unlocked_step = max(
            self._maximum_unlocked_step,
            3,
        )

        self.sidebar.set_unlocked_step(self._maximum_unlocked_step)

        self._show_step(3)