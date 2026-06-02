from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.localization.texts import text


class StatusHeader(QFrame):

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("statusHeader")

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(26, 18, 26, 18)
        layout.setSpacing(26)

        branding = QWidget()
        branding_layout = QVBoxLayout(branding)
        branding_layout.setContentsMargins(0, 0, 0, 0)
        branding_layout.setSpacing(3)

        title = QLabel(text("app_title"))
        title.setObjectName("appTitle")

        subtitle = QLabel(text("app_subtitle"))
        subtitle.setObjectName("appSubtitle")

        branding_layout.addWidget(title)
        branding_layout.addWidget(subtitle)

        self.model_value = QLabel(text("not_selected"))
        self.export_value = QLabel(text("not_selected"))

        layout.addWidget(branding)
        layout.addStretch()
        layout.addWidget(
            self._create_status_item(text("header_model"), self.model_value)
        )
        layout.addWidget(
            self._create_status_item(text("header_export"), self.export_value)
        )

    @staticmethod
    def _create_status_item(label_text: str, value_label: QLabel) -> QWidget:
        item = QWidget()
        item.setObjectName("headerStatusItem")

        layout = QVBoxLayout(item)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(4)

        label = QLabel(label_text)
        label.setObjectName("headerStatusLabel")

        value_label.setObjectName("headerStatusValue")

        layout.addWidget(label)
        layout.addWidget(value_label)

        return item