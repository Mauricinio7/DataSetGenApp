from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoInfo:
    path: Path
    width: int
    height: int
    fps: float
    duration_seconds: float
    file_size_bytes: int

    @property
    def file_name(self) -> str:
        return self.path.name

    @property
    def resolution_text(self) -> str:
        return f"{self.width} × {self.height}"

    @property
    def fps_text(self) -> str:
        return f"{self.fps:.2f}"

    @property
    def duration_text(self) -> str:
        total_seconds = max(0, round(self.duration_seconds))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return f"{minutes:02d}:{seconds:02d}"

    @property
    def file_size_text(self) -> str:
        size = float(self.file_size_bytes)

        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.2f} {unit}"
            size /= 1024

        return f"{size:.2f} GB"