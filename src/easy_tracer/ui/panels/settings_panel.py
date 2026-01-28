from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets
from easy_tracer.services.config_service import ConfigService


class SettingsPanel(QtWidgets.QWidget):
    def __init__(self, config_service: ConfigService):
        super().__init__()
        self.config_service = config_service

        self.adb_input = QtWidgets.QLineEdit(self.config_service.adb_path)
        self.output_input = QtWidgets.QLineEdit(self.config_service.output_dir)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.save_button = QtWidgets.QPushButton("Save Settings")
        self.status_label = QtWidgets.QLabel("")

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("ADB Path:", self.adb_input)

        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(self.output_input, 1)
        output_row.addWidget(self.browse_button)
        form_layout.addRow("Output Dir:", output_row)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Settings"))
        layout.addLayout(form_layout)
        layout.addWidget(self.save_button)
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
        self.status_label.setText("Saved. Restart app to apply changes.")
