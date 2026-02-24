from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets


class OutputPathWidget(QtWidgets.QWidget):
    def __init__(self, default_path: str, *, label: str = "Output:", editable: bool = True, tooltip: str | None = None):
        super().__init__()
        self.path_input = QtWidgets.QLineEdit(default_path)
        self.path_input.setPlaceholderText("Output Directory")
        if tooltip:
            self.path_input.setToolTip(tooltip)
        self.browse_button = QtWidgets.QToolButton()
        self.browse_button.setText("...")
        self.browse_button.setToolTip("Browse")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(QtWidgets.QLabel(label))
        layout.addWidget(self.path_input, 1)
        layout.addWidget(self.browse_button)

        self.browse_button.clicked.connect(self._on_browse)
        self.set_editable(editable)

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

    def set_output_dir(self, path: str) -> None:
        path = (path or "").strip()
        if path:
            self.path_input.setText(path)

    def set_editable(self, editable: bool) -> None:
        # When tool panels show output directory, we want it to be shared/global
        # (edited only in Settings) to avoid duplicated configuration.
        self.path_input.setReadOnly(not editable)
        self.browse_button.setVisible(bool(editable))
