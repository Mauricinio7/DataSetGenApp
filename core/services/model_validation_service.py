from pathlib import Path
from platform import system

import numpy as np
import torch
from ultralytics import YOLO

from core.models.model_info import (
    ExecutionBackend,
    ModelFormat,
    ModelInfo,
)


class ModelCompatibilityError(ValueError):
    """Error provocado cuando un modelo no puede ejecutarse en este equipo."""


class ModelValidationService:
    """Valida que un modelo YOLO pueda ejecutarse en el dispositivo actual."""

    SUPPORTED_EXTENSIONS: dict[str, ModelFormat] = {
        ".pt": ModelFormat.PYTORCH,
        ".onnx": ModelFormat.ONNX,
        ".engine": ModelFormat.TENSORRT,
    }

    @classmethod
    def validate(cls, model_path: Path) -> ModelInfo:
        model_format = cls._get_model_format(model_path)

        if model_format == ModelFormat.TENSORRT:
            return cls._validate_tensorrt_model(model_path)

        if model_format == ModelFormat.ONNX:
            return cls._validate_onnx_model(model_path)

        return cls._validate_pytorch_model(model_path)

    @classmethod
    def _get_model_format(cls, model_path: Path) -> ModelFormat:
        if not model_path.exists() or not model_path.is_file():
            raise ModelCompatibilityError(
                f"El archivo seleccionado no existe: {model_path}"
            )

        extension = model_path.suffix.lower()

        if extension not in cls.SUPPORTED_EXTENSIONS:
            raise ModelCompatibilityError(
                "Formato no compatible. Selecciona un modelo .pt, .onnx o .engine."
            )

        return cls.SUPPORTED_EXTENSIONS[extension]

    @classmethod
    def _validate_pytorch_model(cls, model_path: Path) -> ModelInfo:
        validation_attempts: list[tuple[str | int, ExecutionBackend, str]] = []

        if torch.cuda.is_available():
            validation_attempts.append(
                (
                    0,
                    ExecutionBackend.CUDA,
                    torch.cuda.get_device_name(0),
                )
            )

        if cls._mps_is_available():
            validation_attempts.append(
                (
                    "mps",
                    ExecutionBackend.MPS,
                    "Apple Metal (MPS)",
                )
            )

        validation_attempts.append(
            (
                "cpu",
                ExecutionBackend.CPU,
                "CPU",
            )
        )

        errors: list[str] = []

        for device, backend, device_name in validation_attempts:
            try:
                cls._run_inference_test(model_path, device)

                return ModelInfo(
                    path=model_path,
                    model_format=ModelFormat.PYTORCH,
                    file_size_bytes=model_path.stat().st_size,
                    execution_backend=backend,
                    device_name=device_name,
                )
            except Exception as error:
                errors.append(f"{device_name}: {error}")

        raise ModelCompatibilityError(
            "El modelo PyTorch no pudo ejecutarse en este dispositivo.\n\n"
            + "\n".join(errors)
        )

    @classmethod
    def _validate_onnx_model(cls, model_path: Path) -> ModelInfo:
        try:
            cls._run_inference_test(model_path, "cpu")
        except Exception as error:
            raise ModelCompatibilityError(
                "El modelo ONNX no pudo ejecutarse en este dispositivo.\n\n"
                f"Detalle: {error}"
            ) from error

        return ModelInfo(
            path=model_path,
            model_format=ModelFormat.ONNX,
            file_size_bytes=model_path.stat().st_size,
            execution_backend=ExecutionBackend.CPU,
            device_name="CPU / ONNX Runtime",
        )

    @classmethod
    def _validate_tensorrt_model(cls, model_path: Path) -> ModelInfo:
        if system() == "Darwin":
            raise ModelCompatibilityError(
                "Los modelos TensorRT (.engine) no pueden ejecutarse en macOS. "
                "Selecciona un modelo .pt o .onnx para este equipo."
            )

        if not torch.cuda.is_available():
            raise ModelCompatibilityError(
                "El modelo TensorRT requiere una GPU NVIDIA compatible "
                "y CUDA disponible."
            )

        try:
            cls._run_inference_test(model_path, 0)
        except Exception as error:
            raise ModelCompatibilityError(
                "El modelo TensorRT no pudo ejecutarse con la GPU disponible.\n\n"
                f"Detalle: {error}"
            ) from error

        return ModelInfo(
            path=model_path,
            model_format=ModelFormat.TENSORRT,
            file_size_bytes=model_path.stat().st_size,
            execution_backend=ExecutionBackend.TENSORRT,
            device_name=torch.cuda.get_device_name(0),
        )

    @staticmethod
    def _run_inference_test(model_path: Path, device: str | int) -> None:
        model = YOLO(str(model_path), task="detect")

        test_image = np.zeros((640, 640, 3), dtype=np.uint8)

        model.predict(
            source=test_image,
            imgsz=640,
            conf=0.25,
            device=device,
            verbose=False,
            save=False,
        )

    @staticmethod
    def _mps_is_available() -> bool:
        return (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        )