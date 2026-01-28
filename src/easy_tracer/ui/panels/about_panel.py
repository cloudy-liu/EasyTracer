from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class AboutPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        text = (
            "EasyTracer v1.0.0\n\n"
            "Android Performance Tracing Tool\n"
            "Systrace / Perfetto / Simpleperf / Traceview\n\n"
            "License: MIT\n"
        )

        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("About"))
        layout.addWidget(label)
        link_row = QtWidgets.QHBoxLayout()
        link_row.addWidget(QtWidgets.QLabel("GitHub:"))
        self.link_label = QtWidgets.QLabel("https://github.com/user/EasyTracer")
        self.link_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        open_button = QtWidgets.QPushButton("Open in Browser")
        open_button.clicked.connect(self._open_link)
        link_row.addWidget(self.link_label, 1)
        link_row.addWidget(open_button)
        layout.addLayout(link_row)
        layout.addStretch(1)

    def _open_link(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.link_label.text()))
