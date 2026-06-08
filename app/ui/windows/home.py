from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.localization.texts import text
from app.ui.pages.analysis_page import AnalysisPage
from app.ui.pages.placeholder_page import PlaceholderPage
from app.ui.pages.select_export_path_page import SelectExportPathPage
from app.ui.pages.select_model_page import SelectModelPage
from app.ui.pages.upload_video_page import UploadVideoPage
from app.ui.widgets.status_header import StatusHeader
from app.ui.widgets.step_sidebar import StepSidebar
from app.ui.widgets.video_preview_panel import VideoPreviewPanel
from app.ui.widgets.workflow_footer import WorkflowFooter
from core.models.dataset_workspace import DatasetWorkspace
from core.models.model_info import ModelInfo
from core.models.video_info import VideoInfo
from core.services.dataset_workspace_service import (
    DatasetWorkspaceError,
    DatasetWorkspaceService,
)
from workers.analysis_worker import AnalysisWorker


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(text("app_title"))
        self._configure_size()

        self._current_step = 0
        self._maximum_unlocked_step = 0

        self._video_info: VideoInfo | None = None
        self._model_info: ModelInfo | None = None
        self._export_base_directory: Path | None = None
        self._dataset_workspace: DatasetWorkspace | None = None

        self._video_is_selected = False
        self._model_is_selected = False
        self._export_path_is_selected = False
        self._workspace_is_created = False

        self._analysis_is_running = False
        self._analysis_is_finished = False

        self._analysis_thread: QThread | None = None
        self._analysis_worker: AnalysisWorker | None = None

        self._build_ui()
        self._connect_events()
        self._show_step(0)

    def _configure_size(self) -> None:
        screen = QApplication.primaryScreen()

        if screen is None:
            raise RuntimeError("No se pudo detectar la pantalla principal.")

        available_geometry = screen.availableGeometry()

        self.resize(
            available_geometry.width(),
            available_geometry.height(),
        )

        self.setMinimumSize(
            int(available_geometry.width() * 0.5),
            int(available_geometry.height() * 0.75),
        )

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
        self.pages.setMinimumWidth(350)
        self.pages.setMaximumWidth(390)

        self.upload_video_page = UploadVideoPage()
        self.select_model_page = SelectModelPage()
        self.select_export_path_page = SelectExportPathPage()
        self.analysis_page = AnalysisPage()

        self.placeholder_page = PlaceholderPage(
            text("placeholder_analysis_message")
        )

        self.pages.addWidget(self.upload_video_page)
        self.pages.addWidget(self.select_model_page)
        self.pages.addWidget(self.select_export_path_page)
        self.pages.addWidget(self.analysis_page)
        self.pages.addWidget(self.placeholder_page)

        workspace = QWidget()
        workspace.setObjectName("workspaceContainer")

        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(22, 20, 22, 20)
        workspace_layout.setSpacing(18)

        workspace_layout.addWidget(self.sidebar)
        workspace_layout.addWidget(self.video_preview, 1)
        workspace_layout.addWidget(self.pages)

        root_layout.addWidget(self.header)
        root_layout.addWidget(workspace, 1)
        root_layout.addWidget(self.footer)

    def _connect_events(self) -> None:
        self.upload_video_page.video_selected.connect(
            self._on_video_selected
        )

        self.select_model_page.model_selected.connect(
            self._on_model_selected
        )

        self.select_model_page.model_invalidated.connect(
            self._on_model_invalidated
        )

        self.select_export_path_page.export_path_selected.connect(
            self._on_export_path_selected
        )

        self.analysis_page.start_requested.connect(
            self._start_analysis
        )

        self.analysis_page.pause_requested.connect(
            self._pause_analysis
        )

        self.analysis_page.resume_requested.connect(
            self._resume_analysis
        )

        self.analysis_page.cancel_requested.connect(
            self._request_cancel_analysis
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
        directory_changed = (
            self._export_base_directory is not None
            and self._export_base_directory != base_directory
        )

        self._export_base_directory = base_directory
        self._export_path_is_selected = True

        if directory_changed:
            self._invalidate_created_workspace()

        if self._current_step == 2:
            self.footer.set_next_enabled(True)

    def _reset_analysis_state(self) -> None:
        self._analysis_is_running = False
        self._analysis_is_finished = False

        self.footer.reset_progress()
        self.analysis_page.set_ready_state()

    def _invalidate_created_workspace(self) -> None:
        self._dataset_workspace = None
        self._workspace_is_created = False

        self._reset_analysis_state()

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
                self.sidebar.set_unlocked_step(
                    self._maximum_unlocked_step
                )
                self._show_step(3)
                return

            self._create_dataset_workspace()
            return

        if self._current_step == 3 and self._analysis_is_finished:
            self._maximum_unlocked_step = max(
                self._maximum_unlocked_step,
                4,
            )
            self.sidebar.set_unlocked_step(self._maximum_unlocked_step)
            self._show_step(4)
            return

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
        elif step_index == 3:
            self.footer.set_next_enabled(self._analysis_is_finished)
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

        if self._video_info is not None:
            target_fps = 5.0

            frame_interval = max(
                1,
                round(self._video_info.fps / target_fps),
            )

            total_video_frames = int(
                self._video_info.duration_seconds
                * self._video_info.fps
            )

            total_frames_to_analyze = max(
                1,
                (total_video_frames + frame_interval - 1)
                // frame_interval,
            )

            self.analysis_page.set_initial_video_metrics(
                video_fps=self._video_info.fps_text,
                target_fps=f"{target_fps:.2f}",
                total_frames=str(total_frames_to_analyze),
            )

        self._show_step(3)

    def _start_analysis(self) -> None:
        if (
            self._video_info is None
            or self._model_info is None
            or self._dataset_workspace is None
        ):
            QMessageBox.warning(
                self,
                text("export_error_title"),
                text("export_error_message"),
            )
            return

        self._analysis_is_running = True
        self._analysis_is_finished = False

        self.footer.set_previous_enabled(False)
        self.footer.set_next_enabled(False)
        self.footer.set_progress_value(0)
        self.footer.set_progress_enabled(True)
        self.footer.set_progress_status(text("analysis_status_running"))

        self.sidebar.set_navigation_enabled(False)

        self.analysis_page.set_running_state()

        self._analysis_thread = QThread(self)
        self._analysis_worker = AnalysisWorker(
            video_info=self._video_info,
            model_info=self._model_info,
            workspace=self._dataset_workspace,
            target_fps=5.0,
            confidence_threshold=0.25,
        )

        self._analysis_worker.moveToThread(self._analysis_thread)

        self._analysis_thread.started.connect(
            self._analysis_worker.run
        )

        self._analysis_worker.progress_changed.connect(
            self._on_analysis_progress_changed
        )

        self._analysis_worker.finished.connect(
            self._on_analysis_finished
        )

        self._analysis_worker.cancelled.connect(
            self._on_analysis_cancelled
        )

        self._analysis_worker.failed.connect(
            self._on_analysis_failed
        )

        self._analysis_worker.finished.connect(
            self._analysis_thread.quit
        )

        self._analysis_worker.cancelled.connect(
            self._analysis_thread.quit
        )

        self._analysis_worker.failed.connect(
            self._analysis_thread.quit
        )

        self._analysis_worker.finished.connect(
            self._analysis_worker.deleteLater
        )

        self._analysis_worker.cancelled.connect(
            self._analysis_worker.deleteLater
        )

        self._analysis_worker.failed.connect(
            self._analysis_worker.deleteLater
        )

        self._analysis_thread.finished.connect(
            self._analysis_thread.deleteLater
        )

        self._analysis_thread.finished.connect(
            self._clear_analysis_references
        )

        self._analysis_thread.start()

    def _pause_analysis(self) -> None:
        if self._analysis_worker is None:
            return

        self._analysis_worker.request_pause()
        self.analysis_page.set_paused_state()
        self.footer.set_progress_status(text("analysis_status_paused"))

    def _resume_analysis(self) -> None:
        if self._analysis_worker is None:
            return

        self._analysis_worker.request_resume()
        self.analysis_page.set_running_state()
        self.footer.set_progress_status(text("analysis_status_running"))

    def _request_cancel_analysis(self) -> None:
        response = QMessageBox.question(
            self,
            text("cancel_analysis_title"),
            text("cancel_analysis_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._cancel_analysis()

    def _cancel_analysis(self) -> None:
        if self._analysis_worker is None:
            return

        self.footer.set_progress_status(text("analysis_status_cancelled"))
        self._analysis_worker.request_cancel()

    def _on_analysis_progress_changed(self, progress: dict) -> None:
        progress_percent = progress["progress_percent"]

        self.footer.set_progress_value(progress_percent)

        self.footer.set_progress_status(
            f"Restante: {progress['estimated_time']} · "
            f"Transcurrido: {progress['elapsed_time']} · "
            f"FPS: {progress['processing_rate_fps']:.2f} · "
            f"Frames: {progress['analyzed_frames']}/"
            f"{progress['total_frames']}"
        )

        self.analysis_page.update_progress_metrics(
            analyzed_frames=progress["analyzed_frames"],
            total_frames=progress["total_frames"],
            remaining_frames=progress["remaining_frames"],
            processed_video_time=progress["processed_video_time"],
            estimated_time=progress["estimated_time"],
            processing_rate_fps=progress["processing_rate_fps"],
            detections=progress["detections"],
        )

    def _on_analysis_finished(self) -> None:
        self._analysis_is_running = False
        self._analysis_is_finished = True

        self.sidebar.set_navigation_enabled(True)

        self.footer.set_previous_enabled(True)
        self.footer.set_next_enabled(True)
        self.footer.set_progress_value(100)
        self.footer.set_progress_enabled(True)
        self.footer.set_progress_status(text("analysis_status_finished"))

        self.analysis_page.set_finished_state()

        QMessageBox.information(
            self,
            text("analysis_finished_title"),
            text("analysis_finished_message"),
        )

    def _on_analysis_cancelled(self) -> None:
        self._analysis_is_running = False
        self._analysis_is_finished = False

        self.sidebar.set_navigation_enabled(True)

        self.footer.set_previous_enabled(True)
        self.footer.set_next_enabled(False)
        self.footer.set_progress_value(0)
        self.footer.set_progress_enabled(True)
        self.footer.set_progress_status(text("analysis_status_cancelled"))

        self.analysis_page.set_cancelled_state()
        self.analysis_page.set_initial_video_metrics(
            video_fps=self._video_info.fps_text if self._video_info else text("not_selected"),
            target_fps="5.00",
            total_frames=self.analysis_page.total_frames_value.text(),
        )

    def _on_analysis_failed(self, error_message: str) -> None:
        self._analysis_is_running = False
        self._analysis_is_finished = False

        self.sidebar.set_navigation_enabled(True)

        self.footer.set_previous_enabled(True)
        self.footer.set_next_enabled(False)
        self.footer.set_progress_value(0)
        self.footer.set_progress_enabled(False)
        self.footer.set_progress_status(text("progress_waiting"))

        self.analysis_page.set_cancelled_state()

        QMessageBox.warning(
            self,
            text("export_error_title"),
            error_message,
        )

    def _clear_analysis_references(self) -> None:
        self._analysis_thread = None
        self._analysis_worker = None