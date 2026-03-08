"""
Reusable card and banner widgets for panel UX.

InfoCard       — fills sparse panels with contextual help
ResultCard     — shows capture result summary with action buttons
DeprecationBanner — warns about deprecated tools
"""

from __future__ import annotations

from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets
from easy_tracer.ui.theme import (
    Colors,
    Spacing,
    deprecation_banner_qss,
    info_card_qss,
    result_card_qss,
)


# =============================================================================
# DEPRECATION BANNER
# =============================================================================

class DeprecationBanner(QtWidgets.QFrame):
    """Warning banner for deprecated tools."""

    link_clicked = QtCore.Signal()

    def __init__(
        self,
        message: str,
        link_text: Optional[str] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("deprecationBanner")
        self.setStyleSheet(deprecation_banner_qss())

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.MD)

        icon = QtWidgets.QLabel("⚠")
        icon.setStyleSheet(f"font-size: 16px; color: {Colors.WARNING_DARK};")
        layout.addWidget(icon)

        text = QtWidgets.QLabel(message)
        text.setWordWrap(True)
        layout.addWidget(text, 1)

        if link_text:
            link = QtWidgets.QPushButton(link_text)
            link.setFlat(True)
            link.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            link.setStyleSheet(
                f"color: {Colors.INFO_DARK}; text-decoration: underline; border: none;"
            )
            link.clicked.connect(self.link_clicked.emit)
            layout.addWidget(link)


# =============================================================================
# INFO CARD
# =============================================================================

class InfoCard(QtWidgets.QFrame):
    """Informational card that fills empty panel space."""

    def __init__(
        self,
        title: str,
        description: str,
        bullets: Optional[List[str]] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("infoCard")
        self.setStyleSheet(info_card_qss())

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.MD)

        heading = QtWidgets.QLabel(title)
        heading.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {Colors.NEUTRAL_800};"
        )
        layout.addWidget(heading)

        desc = QtWidgets.QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"line-height: 1.5; color: {Colors.NEUTRAL_600};")
        layout.addWidget(desc)

        if bullets:
            for item in bullets:
                bullet = QtWidgets.QLabel(f"\u2022  {item}")
                bullet.setWordWrap(True)
                bullet.setStyleSheet(f"color: {Colors.NEUTRAL_600}; padding-left: 8px;")
                layout.addWidget(bullet)


# =============================================================================
# RESULT CARD
# =============================================================================

class ResultCard(QtWidgets.QFrame):
    """Capture result summary card with action buttons."""

    open_output_clicked = QtCore.Signal()
    view_trace_clicked = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setObjectName("resultCard")
        self.setStyleSheet(result_card_qss())
        self.setVisible(False)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        self._layout.setSpacing(Spacing.MD)

        self._title = QtWidgets.QLabel("Capture Complete")
        self._title.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {Colors.SUCCESS_DARK};"
        )
        self._layout.addWidget(self._title)

        self._details = QtWidgets.QLabel()
        self._details.setWordWrap(True)
        self._layout.addWidget(self._details)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(Spacing.MD)

        self._view_btn = QtWidgets.QPushButton("View in Perfetto UI")
        self._view_btn.setStyleSheet(
            f"background-color: {Colors.PRIMARY}; color: {Colors.ON_PRIMARY};"
            f"border: 1px solid {Colors.PRIMARY_DARK}; border-radius: 8px;"
            f"padding: 4px 12px;"
        )
        self._view_btn.clicked.connect(self.view_trace_clicked.emit)
        self._view_btn.setVisible(False)
        btn_row.addWidget(self._view_btn)

        self._open_btn = QtWidgets.QPushButton("\U0001f4c2 Open Output Folder")
        self._open_btn.clicked.connect(self.open_output_clicked.emit)
        btn_row.addWidget(self._open_btn)

        btn_row.addStretch()
        self._layout.addLayout(btn_row)

    def show_result(
        self,
        file_name: str,
        file_size: str = "",
        duration: str = "",
        auxiliary: str = "",
        show_perfetto_btn: bool = False,
    ) -> None:
        lines = [f"<b>File:</b> {file_name}"]
        if file_size:
            lines.append(f"<b>Size:</b> {file_size}")
        if duration:
            lines.append(f"<b>Duration:</b> {duration}")
        if auxiliary:
            lines.append(f"<b>Auxiliary:</b> {auxiliary}")
        self._details.setText("<br>".join(lines))
        self._view_btn.setVisible(show_perfetto_btn)
        self.setVisible(True)

    def clear(self) -> None:
        self.setVisible(False)
