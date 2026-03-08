from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from easy_tracer.ui.theme import Colors, Spacing, Typography


class AboutPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        title = QtWidgets.QLabel("EasyTracer")
        title.setStyleSheet(
            f"font-size: {Typography.SIZE_HEADLINE}px; font-weight: 700; color: {Colors.NEUTRAL_900};"
        )

        version = QtWidgets.QLabel("Version 1.0.0 · Android Performance Profiling Suite")
        version.setStyleSheet(f"color: {Colors.NEUTRAL_600};")

        description = QtWidgets.QLabel(
            "EasyTracer simplifies Android performance profiling with a unified UI for "
            "Systrace, Perfetto, Simpleperf, and Traceview."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {Colors.NEUTRAL_600}; line-height: 1.5;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.LG)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(description)

        link_row = QtWidgets.QHBoxLayout()
        link_row.setSpacing(Spacing.MD)
        link_row.addWidget(QtWidgets.QLabel("GitHub:"))
        self.link_label = QtWidgets.QLabel("https://github.com/user/EasyTracer")
        self.link_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        open_button = QtWidgets.QPushButton("GitHub Repository")
        open_button.clicked.connect(self._open_link)
        link_row.addWidget(self.link_label, 1)
        link_row.addWidget(open_button)
        layout.addLayout(link_row)
        layout.addStretch(1)

    def _open_link(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.link_label.text()))
