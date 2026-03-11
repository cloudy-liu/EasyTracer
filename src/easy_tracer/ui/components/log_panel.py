from __future__ import annotations

from PySide6 import QtGui, QtWidgets


_COLLAPSED_GLYPH = "\u25b8"
_EXPANDED_GLYPH = "\u25be"


class LogPanel(QtWidgets.QFrame):
    """Collapsible log panel styled to match the prototype shell."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("logArea")
        self._collapsed = False
        self._last_write_was_stream = False

        self._title = QtWidgets.QLabel("OUTPUT LOG")
        self._title.setObjectName("logHeaderTitle")

        self.toggle_button = QtWidgets.QToolButton()
        self.toggle_button.setObjectName("logToggleButton")
        self.toggle_button.setAutoRaise(True)
        self.toggle_button.clicked.connect(self.toggle_collapsed)

        header = QtWidgets.QFrame()
        header.setObjectName("logHeader")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)
        header_layout.addWidget(self._title)
        header_layout.addStretch(1)
        header_layout.addWidget(self.toggle_button)

        self.text = QtWidgets.QTextEdit()
        self.text.setObjectName("logContent")
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(180)
        self.text.setFont(self._build_monospace_font())

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self.text)

        self._apply_styles()
        self._sync_collapsed_state()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#logArea {
                background-color: #ffffff;
                border-top: 1px solid #e4e7eb;
            }
            QFrame#logHeader {
                background-color: #f8f9fa;
                border-bottom: 1px solid #e4e7eb;
            }
            QLabel#logHeaderTitle {
                color: #757575;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QToolButton#logToggleButton {
                border: none;
                background: transparent;
                color: #757575;
                font-size: 11px;
                padding: 2px;
            }
            QToolButton#logToggleButton:hover {
                color: #212121;
            }
            QTextEdit#logContent {
                border: none;
                background-color: #fafafa;
                color: #616161;
                selection-background-color: #bbdefb;
                padding: 8px 12px;
            }
            """
        )

    def _build_monospace_font(self) -> QtGui.QFont:
        """Builds the best available monospace font for the log view."""

        for family in ("JetBrains Mono", "Cascadia Mono", "Consolas"):
            font = QtGui.QFont(family)
            if QtGui.QFontInfo(font).exactMatch():
                return font
        return QtGui.QFont("monospace")

    def is_collapsed(self) -> bool:
        """Returns whether the log body is currently collapsed."""

        return self._collapsed

    def toggle_collapsed(self) -> None:
        """Toggles the log body visibility."""

        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Updates the collapsed state for the log body."""

        self._collapsed = bool(collapsed)
        self._sync_collapsed_state()

    def _sync_collapsed_state(self) -> None:
        self.text.setVisible(not self._collapsed)
        glyph = _COLLAPSED_GLYPH if self._collapsed else _EXPANDED_GLYPH
        self.toggle_button.setText(glyph)
        self.setMinimumHeight(32 if self._collapsed else 188)

    def append(self, message: str) -> None:
        """Appends a complete log line."""

        if not message:
            return
        self.text.append(message)
        self._last_write_was_stream = False
        self.text.ensureCursorVisible()

    def append_stream(self, message: str) -> None:
        """Appends raw log output without forcing a trailing newline."""

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
        """Clears the log contents."""

        self.text.clear()
        self._last_write_was_stream = False
