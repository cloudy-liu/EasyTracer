from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from easy_tracer.ui.theme import Colors, Spacing, Typography


class AboutPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        repo_url = "https://github.com/cloudy-liu/EasyTracer"

        title = QtWidgets.QLabel("EasyTracer")
        title.setStyleSheet(
            f"font-size: {Typography.SIZE_HEADLINE}px; font-weight: 700; color: {Colors.NEUTRAL_900};"
        )

        version = QtWidgets.QLabel("Version 1.0.0 | Android Performance Profiling Suite")
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
        link_row.addWidget(QtWidgets.QLabel("Repository:"))
        self.link_label = QtWidgets.QLabel(f'<a href="{repo_url}">{repo_url}</a>')
        self.link_label.setOpenExternalLinks(True)
        self.link_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.link_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.link_label.setStyleSheet(
            f"color: {Colors.PRIMARY_DARK}; text-decoration: underline;"
        )
        link_row.addWidget(self.link_label, 1)
        layout.addLayout(link_row)
        layout.addStretch(1)
