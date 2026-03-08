from __future__ import annotations

from pathlib import Path
from PySide6 import QtCore, QtWidgets

from easy_tracer.services.config_service import ConfigService
from easy_tracer.ui.theme import Colors, Spacing, Typography


class SettingsPanel(QtWidgets.QWidget):
    settings_saved = QtCore.Signal(str, str)  # adb_path, output_dir

    def __init__(self, config_service: ConfigService):
        super().__init__()
        self.config_service = config_service

        title = QtWidgets.QLabel("Settings")
        title.setStyleSheet(
            f"font-size: {Typography.SIZE_TITLE}px; font-weight: 600; color: {Colors.NEUTRAL_800};"
        )
        subtitle = QtWidgets.QLabel("Configure the shared ADB path and default output directory.")
        subtitle.setStyleSheet(f"color: {Colors.NEUTRAL_600};")

        self.adb_input = QtWidgets.QLineEdit(self.config_service.adb_path)
        self.output_input = QtWidgets.QLineEdit(self.config_service.output_dir)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.save_button = QtWidgets.QPushButton("Save Settings")
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet(f"color: {Colors.SUCCESS_DARK};")

        form_layout = QtWidgets.QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setHorizontalSpacing(Spacing.LG)
        form_layout.setVerticalSpacing(Spacing.LG)
        form_layout.addRow("ADB Path:", self.adb_input)

        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(self.output_input, 1)
        output_row.addWidget(self.browse_button)
        form_layout.addRow("Output Dir:", output_row)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.save_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.LG)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form_layout)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.browse_button.clicked.connect(self._on_browse)
        self.save_button.clicked.connect(self._on_save)

    def _on_browse(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            str(Path(self.output_input.text() or ".").resolve()),
        )
        if directory:
            self.output_input.setText(directory)

    def _on_save(self) -> None:
        adb_path = self.adb_input.text().strip() or "adb"
        output_dir = self.output_input.text().strip()
        self.config_service.update(adb_path=adb_path, output_dir=output_dir)
        self.status_label.setText("Saved and applied.")
        self.settings_saved.emit(self.config_service.adb_path, self.config_service.output_dir)
