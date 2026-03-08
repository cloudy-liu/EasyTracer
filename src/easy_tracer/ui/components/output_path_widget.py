from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtWidgets


class OutputPathWidget(QtWidgets.QWidget):
    output_dir_changed = QtCore.Signal(str)

    def __init__(self, default_path: str, *, label: str = "Output:", editable: bool = True, tooltip: str | None = None):
        super().__init__()
        self.setObjectName("outputPathWidget")
        self.path_input = QtWidgets.QLineEdit(default_path)
        self._last_emitted_output_dir = (default_path or "").strip()
        self.path_input.setPlaceholderText("Output Directory")
        if tooltip:
            self.path_input.setToolTip(tooltip)

        self.label = QtWidgets.QLabel(label)
        self.label.setProperty("toolbarLabel", True)

        self.browse_button = QtWidgets.QToolButton()
        self.browse_button.setText("…")
        self.browse_button.setToolTip("Browse for directory")
        self.browse_button.setFixedWidth(32)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.label)
        layout.addWidget(self.path_input, 1)
        layout.addWidget(self.browse_button)

        self.browse_button.clicked.connect(self._on_browse)
        self.path_input.editingFinished.connect(self._emit_output_dir_changed)
        self.set_editable(editable)

    def _on_browse(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            str(Path(self.path_input.text() or ".").resolve()),
        )
        if directory:
            self.path_input.setText(directory)
            self._emit_output_dir_changed()

    def _emit_output_dir_changed(self) -> None:
        output_dir = self.output_dir()
        if not output_dir or output_dir == self._last_emitted_output_dir:
            return
        self._last_emitted_output_dir = output_dir
        self.output_dir_changed.emit(output_dir)

    def output_dir(self) -> str:
        return self.path_input.text().strip()

    def set_output_dir(self, path: str) -> None:
        path = (path or "").strip()
        if path:
            self._last_emitted_output_dir = path
            self.path_input.setText(path)

    def set_editable(self, editable: bool) -> None:
        # Tool panels share one global output directory; editable widgets let the
        # user change it from any panel while MainWindow keeps everything synced.
        self.path_input.setReadOnly(not editable)
        self.browse_button.setVisible(bool(editable))
