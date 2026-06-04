from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ModelFormat(Enum):
    PYTORCH = "pt"
    ONNX = "onnx"
    TENSORRT = "engine"


class ExecutionBackend(Enum):
    CPU = "cpu"
    MPS = "mps"
    CUDA = "cuda"
    TENSORRT = "tensorrt"


@dataclass(frozen=True)
class ModelInfo:
    path: Path
    model_format: ModelFormat
    file_size_bytes: int
    execution_backend: ExecutionBackend
    device_name: str

    @property
    def file_name(self) -> str:
        return self.path.name

    @property
    def file_size_text(self) -> str:
        size = float(self.file_size_bytes)

        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.2f} {unit}"

            size /= 1024

        return f"{size:.2f} GB"