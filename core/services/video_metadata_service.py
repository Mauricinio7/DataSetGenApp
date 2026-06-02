from pathlib import Path

import cv2

from core.models.video_info import VideoInfo


class VideoMetadataService:

    @staticmethod
    def read(video_path: Path) -> VideoInfo:
        capture = cv2.VideoCapture(str(video_path))

        if not capture.isOpened():
            capture.release()
            raise ValueError(f"No se pudo abrir el video: {video_path}")

        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

        capture.release()

        duration_seconds = total_frames / fps if fps > 0 else 0.0

        return VideoInfo(
            path=video_path,
            width=width,
            height=height,
            fps=fps,
            duration_seconds=duration_seconds,
            file_size_bytes=video_path.stat().st_size,
        )