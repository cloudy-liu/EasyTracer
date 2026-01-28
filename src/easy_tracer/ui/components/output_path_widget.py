from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets


class OutputPathWidget(QtWidgets.QWidget):
    def __init__(self, default_path: str):
        super().__init__()
        self.path_input = QtWidgets.QLineEdit(default_path)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.subfolder_cb = QtWidgets.QCheckBox("为每次抓取创建单独文件夹")

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.path_input, 1)
        row.addWidget(self.browse_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.subfolder_cb)

        self.browse_button.clicked.connect(self._on_browse)

    def _on_browse(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            str(Path(self.path_input.text() or ".").resolve()),
        )
        if directory:
            self.path_input.setText(directory)

    def output_dir(self) -> str:
        return self.path_input.text().strip()

    def create_subfolder(self) -> bool:
        return self.subfolder_cb.isChecked()
