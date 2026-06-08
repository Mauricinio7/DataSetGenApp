import shutil
import time
from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import QObject, QMutex, QWaitCondition, Signal, Slot
from ultralytics import YOLO

from core.models.dataset_workspace import DatasetWorkspace
from core.models.model_info import ExecutionBackend, ModelInfo
from core.models.video_info import VideoInfo


class AnalysisWorker(QObject):

    progress_changed = Signal(dict)
    finished = Signal()
    cancelled = Signal()
    failed = Signal(str)

    def __init__(
        self,
        video_info: VideoInfo,
        model_info: ModelInfo,
        workspace: DatasetWorkspace,
        target_fps: float = 5.0,
        confidence_threshold: float = 0.25,
    ) -> None:
        super().__init__()

        self._video_info = video_info
        self._model_info = model_info
        self._workspace = workspace
        self._target_fps = target_fps
        self._confidence_threshold = confidence_threshold

        self._cancel_requested = False
        self._pause_requested = False

        self._mutex = QMutex()
        self._pause_condition = QWaitCondition()

        self._started_at: datetime | None = None
        self._finished_at: datetime | None = None

        self._last_summary: dict = {
            "analyzed_frames": 0,
            "total_frames": 0,
            "remaining_frames": 0,
            "processed_video_time": "00:00",
            "elapsed_time": "00:00",
            "estimated_time": "00:00",
            "processing_rate_fps": 0.0,
            "detections": 0,
            "saved_items": 0,
            "progress_percent": 0,
        }

    @Slot()
    def run(self) -> None:
        try:
            self._process_video()
        except Exception as error:
            self._finished_at = datetime.now()
            self._update_info_file(
                final_status="FAILED",
                status_message=str(error),
            )
            self.failed.emit(str(error))

    def request_pause(self) -> None:
        self._mutex.lock()
        self._pause_requested = True
        self._mutex.unlock()

    def request_resume(self) -> None:
        self._mutex.lock()
        self._pause_requested = False
        self._pause_condition.wakeAll()
        self._mutex.unlock()

    def request_cancel(self) -> None:
        self._mutex.lock()
        self._cancel_requested = True
        self._pause_requested = False
        self._pause_condition.wakeAll()
        self._mutex.unlock()

    def _process_video(self) -> None:
        self._started_at = datetime.now()

        self._update_info_file(
            final_status="RUNNING",
            status_message="Analysis started.",
        )

        model = YOLO(str(self._model_info.path))

        capture = cv2.VideoCapture(str(self._video_info.path))

        if not capture.isOpened():
            raise RuntimeError("No se pudo abrir el video para análisis.")

        original_fps = capture.get(cv2.CAP_PROP_FPS)

        if original_fps <= 0:
            original_fps = self._video_info.fps

        total_video_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_interval = max(
            1,
            round(original_fps / self._target_fps),
        )

        total_frames_to_analyze = max(
            1,
            (total_video_frames + frame_interval - 1) // frame_interval,
        )

        analyzed_frames = 0
        saved_items = 0
        detections_count = 0

        start_time = time.time()
        frame_index = 0

        device_argument = self._device_argument()

        while True:
            self._wait_if_paused()

            if self._is_cancel_requested():
                capture.release()

                elapsed_seconds = time.time() - start_time
                self._finished_at = datetime.now()

                self._last_summary.update(
                    {
                        "elapsed_time": self._format_seconds(
                            elapsed_seconds
                        ),
                        "remaining_frames": max(
                            0,
                            total_frames_to_analyze - analyzed_frames,
                        ),
                        "progress_percent": int(
                            (
                                analyzed_frames
                                / total_frames_to_analyze
                            )
                            * 100
                        )
                        if total_frames_to_analyze > 0
                        else 0,
                    }
                )

                self._clear_generated_outputs()

                self._update_info_file(
                    final_status="CANCELLED",
                    status_message=(
                        "Analysis cancelled by user. Generated images, "
                        "labels and previews were removed."
                    ),
                )

                self.cancelled.emit()
                return

            success, frame = capture.read()

            if not success:
                break

            if frame_index % frame_interval != 0:
                frame_index += 1
                continue

            results = model.predict(
                source=frame,
                conf=self._confidence_threshold,
                verbose=False,
                device=device_argument,
            )

            result = results[0]
            boxes = result.boxes

            if boxes is not None and len(boxes) > 0:
                detections_for_frame = len(boxes)
                detections_count += detections_for_frame
                saved_items += 1

                base_name = f"frame_{frame_index:08d}"

                image_path = (
                    self._workspace.images_directory
                    / f"{base_name}.jpg"
                )
                label_path = (
                    self._workspace.labels_directory
                    / f"{base_name}.txt"
                )
                preview_path = (
                    self._workspace.previews_directory
                    / f"{base_name}.jpg"
                )

                cv2.imwrite(str(image_path), frame)
                self._write_yolo_label(label_path, boxes)
                self._write_preview(preview_path, frame, boxes)

            analyzed_frames += 1
            frame_index += 1

            elapsed_seconds = time.time() - start_time

            processing_rate = (
                analyzed_frames / elapsed_seconds
                if elapsed_seconds > 0
                else 0.0
            )

            remaining_frames = max(
                0,
                total_frames_to_analyze - analyzed_frames,
            )

            estimated_seconds = (
                remaining_frames / processing_rate
                if processing_rate > 0
                else 0.0
            )

            processed_video_seconds = frame_index / original_fps

            progress_percent = int(
                (analyzed_frames / total_frames_to_analyze) * 100
            )

            progress = {
                "progress_percent": progress_percent,
                "analyzed_frames": analyzed_frames,
                "total_frames": total_frames_to_analyze,
                "remaining_frames": remaining_frames,
                "processed_video_time": self._format_seconds(
                    processed_video_seconds
                ),
                "elapsed_time": self._format_seconds(elapsed_seconds),
                "estimated_time": self._format_seconds(estimated_seconds),
                "processing_rate_fps": processing_rate,
                "detections": detections_count,
                "saved_items": saved_items,
            }

            self._last_summary.update(progress)
            self.progress_changed.emit(progress)

        capture.release()

        total_elapsed_seconds = time.time() - start_time
        self._finished_at = datetime.now()

        final_processing_rate = (
            analyzed_frames / total_elapsed_seconds
            if total_elapsed_seconds > 0
            else 0.0
        )

        final_progress = {
            "progress_percent": 100,
            "analyzed_frames": analyzed_frames,
            "total_frames": total_frames_to_analyze,
            "remaining_frames": 0,
            "processed_video_time": self._format_seconds(
                self._video_info.duration_seconds
            ),
            "elapsed_time": self._format_seconds(total_elapsed_seconds),
            "estimated_time": "00:00",
            "processing_rate_fps": final_processing_rate,
            "detections": detections_count,
            "saved_items": saved_items,
        }

        self._last_summary.update(final_progress)
        self.progress_changed.emit(final_progress)

        self._update_info_file(
            final_status="FINISHED",
            status_message="Analysis finished successfully.",
        )

        self.finished.emit()

    def _device_argument(self):
        if self._model_info.execution_backend == ExecutionBackend.CUDA:
            return 0

        if self._model_info.execution_backend == ExecutionBackend.MPS:
            return "mps"

        if self._model_info.execution_backend == ExecutionBackend.TENSORRT:
            return 0

        return "cpu"

    def _wait_if_paused(self) -> None:
        self._mutex.lock()

        while self._pause_requested and not self._cancel_requested:
            self._pause_condition.wait(self._mutex)

        self._mutex.unlock()

    def _is_cancel_requested(self) -> bool:
        self._mutex.lock()
        cancel_requested = self._cancel_requested
        self._mutex.unlock()

        return cancel_requested

    def _clear_generated_outputs(self) -> None:
        """Borra los archivos generados, pero conserva la carpeta del dataset."""

        directories_to_clean = (
            self._workspace.images_directory,
            self._workspace.labels_directory,
            self._workspace.previews_directory,
        )

        for directory in directories_to_clean:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                continue

            for item in directory.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    def _update_info_file(
        self,
        final_status: str,
        status_message: str,
    ) -> None:
        """Reescribe Info.txt con la configuración y el último estado."""

        started_at_text = (
            self._started_at.strftime("%Y-%m-%d %H:%M:%S")
            if self._started_at is not None
            else "Not started"
        )

        finished_at_text = (
            self._finished_at.strftime("%Y-%m-%d %H:%M:%S")
            if self._finished_at is not None
            else "Not finished"
        )

        summary = self._last_summary

        info_content = (
            "DATASET GENERATION PROJECT\n"
            "==========================\n\n"
            "SOURCE VIDEO\n"
            "------------\n"
            f"File: {self._video_info.file_name}\n"
            f"Path: {self._video_info.path}\n"
            f"Resolution: {self._video_info.resolution_text}\n"
            f"FPS: {self._video_info.fps_text}\n"
            f"Duration: {self._video_info.duration_text}\n"
            f"Size: {self._video_info.file_size_text}\n\n"
            "DETECTION MODEL\n"
            "---------------\n"
            f"File: {self._model_info.file_name}\n"
            f"Path: {self._model_info.path}\n"
            f"Format: {self._model_info.model_format.value}\n"
            f"Execution backend: "
            f"{self._model_info.execution_backend.value}\n"
            f"Device: {self._model_info.device_name}\n"
            f"Size: {self._model_info.file_size_text}\n\n"
            "OUTPUT WORKSPACE\n"
            "----------------\n"
            f"Root directory: {self._workspace.root_directory}\n"
            f"Images directory: {self._workspace.images_directory}\n"
            f"Labels directory: {self._workspace.labels_directory}\n"
            f"Previews directory: {self._workspace.previews_directory}\n"
            f"Info file: {self._workspace.info_file}\n\n"
            "ANALYSIS CONFIGURATION\n"
            "----------------------\n"
            f"Target FPS: {self._target_fps:.2f}\n"
            f"Confidence threshold: {self._confidence_threshold:.2f}\n\n"
            "ANALYSIS EXECUTION\n"
            "------------------\n"
            f"Status: {final_status}\n"
            f"Message: {status_message}\n"
            f"Started at: {started_at_text}\n"
            f"Finished at: {finished_at_text}\n"
            f"Elapsed time: {summary['elapsed_time']}\n"
            f"Progress: {summary['progress_percent']}%\n"
            f"Frames analyzed: "
            f"{summary['analyzed_frames']} / {summary['total_frames']}\n"
            f"Frames remaining: {summary['remaining_frames']}\n"
            f"Video time covered: {summary['processed_video_time']}\n"
            f"Estimated time remaining: {summary['estimated_time']}\n"
            f"Processing speed: "
            f"{summary['processing_rate_fps']:.2f} FPS\n"
            f"Detections: {summary['detections']}\n"
            f"Saved image-label-preview items: {summary['saved_items']}\n"
        )

        self._workspace.info_file.write_text(
            info_content,
            encoding="utf-8",
        )

    @staticmethod
    def _write_yolo_label(label_path: Path, boxes) -> None:
        lines: list[str] = []

        for box in boxes:
            class_id = int(box.cls[0].item())
            x_center, y_center, width, height = box.xywhn[0].tolist()

            lines.append(
                f"{class_id} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{width:.6f} "
                f"{height:.6f}"
            )

        label_path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _write_preview(preview_path: Path, frame, boxes) -> None:
        preview = frame.copy()

        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            cv2.rectangle(
                preview,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),
                2,
            )

        cv2.imwrite(str(preview_path), preview)

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        seconds = max(0, int(seconds))

        minutes, remaining_seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

        return f"{minutes:02d}:{remaining_seconds:02d}"