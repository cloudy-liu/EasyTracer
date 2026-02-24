from __future__ import annotations

from PySide6 import QtGui, QtWidgets


class LogPanel(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.text = QtWidgets.QTextEdit()
        self._last_write_was_stream = False
        self.text.setReadOnly(True)
        # Default log area was too small; keep it comfortably readable.
        self.text.setMinimumHeight(240)
        self.text.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text)

    def append(self, message: str) -> None:
        self.text.append(message)
        self._last_write_was_stream = False
        self.text.ensureCursorVisible()

    def append_stream(self, message: str) -> None:
        """Append raw stream chunks without forcing a newline."""
        if not message:
            return
        cursor = self.text.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        if not self._last_write_was_stream:
            current = self.text.toPlainText()
            if current and not current.endswith("\n") and not message.startswith("\n"):
                cursor.insertText("\n")
        cursor.insertText(message)
        self.text.setTextCursor(cursor)
        self._last_write_was_stream = True
        self.text.ensureCursorVisible()

    def clear(self) -> None:
        self.text.clear()
        self._last_write_was_stream = False
