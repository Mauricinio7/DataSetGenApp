import csv
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
    """Procesa el video con YOLO sin bloquear la interfaz."""

    progress_changed = Signal(dict)
    finished = Signal()
    cancelled = Signal()
    failed = Signal(str)

    CLASS_ID = 0
    CLASS_NAME = "polyp"

    def __init__(
        self,
        video_info: VideoInfo,
        model_info: ModelInfo,
        workspace: DatasetWorkspace,
        target_fps: float = 5.0,
        confidence_threshold: float = 0.70,
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

        self._summary_rows: list[dict] = []

        self._summary_path = (
            self._workspace.root_directory / "detections_summary.csv"
        )

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

        run_name = self._video_info.path.stem
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
                        "labels, previews and summary were removed."
                    ),
                )

                self.cancelled.emit()
                return

            success, frame_bgr = capture.read()

            if not success:
                break

            should_process = frame_index % frame_interval == 0

            if not should_process:
                frame_index += 1
                continue

            analyzed_frames += 1

            frame_rgb = cv2.cvtColor(
                frame_bgr,
                cv2.COLOR_BGR2RGB,
            )

            image_height, image_width = frame_rgb.shape[:2]

            results = model.predict(
                source=frame_rgb,
                conf=self._confidence_threshold,
                verbose=False,
                device=device_argument,
            )

            result = results[0]

            yolo_lines = self._result_to_yolo_lines(
                result=result,
                image_width=image_width,
                image_height=image_height,
                expected_class_id=self.CLASS_ID,
            )

            if len(yolo_lines) > 0:
                timestamp_sec = (
                    frame_index / original_fps
                    if original_fps > 0
                    else 0.0
                )

                base_name = f"{run_name}_f{frame_index:06d}"

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

                cv2.imwrite(str(image_path), frame_bgr)

                label_path.write_text(
                    "\n".join(yolo_lines) + "\n",
                    encoding="utf-8",
                )

                annotated_rgb = result.plot()

                annotated_bgr = cv2.cvtColor(
                    annotated_rgb,
                    cv2.COLOR_RGB2BGR,
                )

                cv2.imwrite(str(preview_path), annotated_bgr)

                confidences = self._get_class_confidences(
                    result=result,
                    expected_class_id=self.CLASS_ID,
                )

                num_boxes = len(confidences)
                detections_count += num_boxes
                saved_items += 1

                self._summary_rows.append(
                    {
                        "video_path": str(self._video_info.path),
                        "run_name": run_name,
                        "frame_idx": frame_index,
                        "timestamp_sec": round(timestamp_sec, 3),
                        "image_path": str(image_path),
                        "label_path": str(label_path),
                        "preview_path": str(preview_path),
                        "num_boxes": num_boxes,
                        "max_confidence": round(
                            max(confidences),
                            6,
                        )
                        if confidences
                        else 0.0,
                        "mean_confidence": round(
                            sum(confidences) / len(confidences),
                            6,
                        )
                        if confidences
                        else 0.0,
                    }
                )

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

        self._write_summary_csv()

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

        if self._summary_path.exists():
            self._summary_path.unlink()

    def _write_summary_csv(self) -> None:
        fieldnames = [
            "video_path",
            "run_name",
            "frame_idx",
            "timestamp_sec",
            "image_path",
            "label_path",
            "preview_path",
            "num_boxes",
            "max_confidence",
            "mean_confidence",
        ]

        with self._summary_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self._summary_rows)

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
            f"Summary CSV: {self._summary_path}\n"
            f"Info file: {self._workspace.info_file}\n\n"
            "ANALYSIS CONFIGURATION\n"
            "----------------------\n"
            f"Class ID: {self.CLASS_ID}\n"
            f"Class name: {self.CLASS_NAME}\n"
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

    def _result_to_yolo_lines(
        self,
        result,
        image_width: int,
        image_height: int,
        expected_class_id: int,
    ) -> list[str]:
        yolo_lines: list[str] = []

        if result.boxes is None:
            return yolo_lines

        for box in result.boxes:
            class_id = int(box.cls[0].item())

            if class_id != expected_class_id:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            x_center, y_center, bbox_width, bbox_height = (
                self._xyxy_to_yolo_bbox(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    image_width=image_width,
                    image_height=image_height,
                )
            )

            yolo_line = (
                f"{class_id} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{bbox_width:.6f} "
                f"{bbox_height:.6f}"
            )

            yolo_lines.append(yolo_line)

        return yolo_lines

    @staticmethod
    def _get_class_confidences(
        result,
        expected_class_id: int,
    ) -> list[float]:
        confidences: list[float] = []

        if result.boxes is None:
            return confidences

        for box in result.boxes:
            class_id = int(box.cls[0].item())

            if class_id != expected_class_id:
                continue

            confidence = float(box.conf[0].item())
            confidences.append(confidence)

        return confidences

    @staticmethod
    def _xyxy_to_yolo_bbox(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        image_width: int,
        image_height: int,
    ) -> tuple[float, float, float, float]:
        x_center = ((x1 + x2) / 2) / image_width
        y_center = ((y1 + y2) / 2) / image_height

        bbox_width = (x2 - x1) / image_width
        bbox_height = (y2 - y1) / image_height

        return x_center, y_center, bbox_width, bbox_height

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        seconds = max(0, int(seconds))

        minutes, remaining_seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

        return f"{minutes:02d}:{remaining_seconds:02d}"