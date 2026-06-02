from typing import Final


TEXTS_ES: Final[dict[str, str]] = {
    "app_title": "DataSet Gen App",
    "app_subtitle": "Generación de datasets con modelos de IA",

    "header_model": "Modelo",
    "header_export": "Exportación",
    "not_selected": "No seleccionado",

    "step_1": "Subir video",
    "step_2": "Seleccionar modelo",
    "step_3": "Ruta de exportación",
    "step_4": "Ejecutar análisis",
    "step_5": "Revisar generados",
    "step_6": "Terminar",

    "upload_title": "Subir video",
    "upload_description": "Selecciona el video que será analizado para generar el dataset.",
    "select_video": "Seleccionar video",
    "change_video": "Cambiar video",
    "video_dialog_title": "Seleccionar video para analizar",
    "video_filter": "Videos (*.mp4 *.avi *.mov *.mkv *.m4v);;Todos los archivos (*)",

    "preview_empty": "Selecciona un video para mostrar la vista previa",
    "play": "Reproducir",
    "pause": "Pausar",
    "stop": "Detener",

    "video_information": "Información del video",
    "video_name": "Archivo",
    "video_resolution": "Resolución",
    "video_fps": "FPS",
    "video_duration": "Duración",
    "video_size": "Tamaño",
    "video_path": "Ruta",

    "progress_title": "Progreso del análisis",
    "progress_waiting": "Esperando configuración",
    "cancel": "Cancelar",
    "previous": "Regresar",
    "continue": "Continuar",

    "placeholder_title": "Siguiente paso",
    "placeholder_model_message": "Aquí configuraremos el modelo de IA que se utilizará para analizar el video.",

    "video_error_title": "No se pudo abrir el video",
    "video_error_message": "El archivo seleccionado no pudo ser leído correctamente.",

    "time_empty": "00:00 / 00:00",
}


def text(key: str) -> str:
    return TEXTS_ES[key]