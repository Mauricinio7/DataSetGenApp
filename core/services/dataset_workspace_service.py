from datetime import datetime
from pathlib import Path

from core.models.dataset_workspace import DatasetWorkspace
from core.models.model_info import ModelInfo
from core.models.video_info import VideoInfo


class DatasetWorkspaceError(ValueError):
    """Error ocurrido al preparar la carpeta de generación del dataset."""


class DatasetWorkspaceService:
    """Crea y documenta el espacio de salida de una generación de dataset."""

    WORKSPACE_PREFIX = "GeneratedDataSet"

    @classmethod
    def create(
        cls,
        base_directory: Path,
        video_info: VideoInfo,
        model_info: ModelInfo,
    ) -> DatasetWorkspace:
        cls._validate_base_directory(base_directory)

        created_at = datetime.now()
        folder_name = (
            f"{cls.WORKSPACE_PREFIX}_"
            f"{created_at.strftime('%Y%m%d_%H%M%S')}"
        )

        root_directory = base_directory / folder_name
        images_directory = root_directory / "images"
        labels_directory = root_directory / "labels"
        previews_directory = root_directory / "previews"
        info_file = root_directory / "Info.txt"

        try:
            images_directory.mkdir(parents=True, exist_ok=False)
            labels_directory.mkdir(parents=True, exist_ok=False)
            previews_directory.mkdir(parents=True, exist_ok=False)
        except OSError as error:
            raise DatasetWorkspaceError(
                "No se pudo crear la estructura del dataset "
                "en la carpeta seleccionada."
            ) from error

        workspace = DatasetWorkspace(
            root_directory=root_directory,
            images_directory=images_directory,
            labels_directory=labels_directory,
            previews_directory=previews_directory,
            info_file=info_file,
        )

        cls._write_initial_info(
            workspace=workspace,
            created_at=created_at,
            video_info=video_info,
            model_info=model_info,
        )

        return workspace

    @staticmethod
    def _validate_base_directory(base_directory: Path) -> None:
        if not base_directory.exists():
            raise DatasetWorkspaceError(
                "La carpeta de exportación seleccionada no existe."
            )

        if not base_directory.is_dir():
            raise DatasetWorkspaceError(
                "La ruta de exportación seleccionada no es una carpeta."
            )

    @staticmethod
    def _write_initial_info(
        workspace: DatasetWorkspace,
        created_at: datetime,
        video_info: VideoInfo,
        model_info: ModelInfo,
    ) -> None:
        info_content = (
            "DATASET GENERATION PROJECT\n"
            "==========================\n\n"
            f"Created at: {created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "SOURCE VIDEO\n"
            "------------\n"
            f"File: {video_info.file_name}\n"
            f"Path: {video_info.path}\n"
            f"Resolution: {video_info.resolution_text}\n"
            f"FPS: {video_info.fps_text}\n"
            f"Duration: {video_info.duration_text}\n"
            f"Size: {video_info.file_size_text}\n\n"
            "DETECTION MODEL\n"
            "---------------\n"
            f"File: {model_info.file_name}\n"
            f"Path: {model_info.path}\n"
            f"Format: {model_info.model_format.value}\n"
            f"Execution backend: {model_info.execution_backend.value}\n"
            f"Device: {model_info.device_name}\n"
            f"Size: {model_info.file_size_text}\n\n"
            "GENERATION STATUS\n"
            "-----------------\n"
            "Status: Workspace created. Analysis has not started.\n"
        )

        try:
            workspace.info_file.write_text(
                info_content,
                encoding="utf-8",
            )
        except OSError as error:
            raise DatasetWorkspaceError(
                "Las carpetas fueron creadas, pero no se pudo escribir "
                "el archivo Info.txt."
            ) from error