"""
Category Selection Dialog
=========================
Modal dialog wrapping CategorySelector for atrace category selection.

Components:
    CategoryDialog        -- Full category picker with OK/Cancel
    CategorySummaryWidget -- Compact chip summary + "Edit" trigger
"""

from typing import Optional

from PySide6 import QtCore, QtWidgets

from easy_tracer.models.category_registry import CATEGORY_DESCRIPTIONS
from easy_tracer.ui.components.category_selector import CategorySelector
from easy_tracer.ui.theme import Colors, Spacing


# =============================================================================
# FLOW LAYOUT
# =============================================================================

class _FlowLayout(QtWidgets.QLayout):
    """Arranges widgets left-to-right, wrapping to next row on overflow."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        h_spacing: int = 4,
        v_spacing: int = 4,
    ):
        super().__init__(parent)
        self._items: list[QtWidgets.QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    # -- QLayout interface --------------------------------------------------

    def addItem(self, item: QtWidgets.QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> Optional[QtWidgets.QLayoutItem]:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> Optional[QtWidgets.QLayoutItem]:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QtCore.QRect(0, 0, width, 0), dry_run=True)

    def setGeometry(self, rect: QtCore.QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, dry_run=False)

    def sizeHint(self) -> QtCore.QSize:
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    # -- Internal -----------------------------------------------------------

    def _do_layout(self, rect: QtCore.QRect, dry_run: bool = False) -> int:
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y = area.x(), area.y()
        row_h = 0

        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            # Wrap to next row when current item overflows
            if x + w > area.right() + 1 and row_h > 0:
                x = area.x()
                y += row_h + self._v_spacing
                row_h = 0
            if not dry_run:
                item.setGeometry(QtCore.QRect(x, y, w, h))
            x += w + self._h_spacing
            row_h = max(row_h, h)

        return y + row_h - rect.y() + m.bottom()


# =============================================================================
# CATEGORY DIALOG
# =============================================================================

class CategoryDialog(QtWidgets.QDialog):
    """Modal wrapper around CategorySelector.

    Usage (static):
        selected, ok = CategoryDialog.select_categories(parent, all_cats, current)
    Usage (instance):
        dlg = CategoryDialog(parent)
        dlg.set_categories(cats, selected)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_selected()
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Atrace Categories")
        self.resize(720, 520)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)

        self._selector = CategorySelector()
        layout.addWidget(self._selector, 1)

        # Button row
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    @property
    def refresh_button(self) -> QtWidgets.QPushButton:
        """Expose inner refresh button for external signal wiring."""
        return self._selector.refresh_button

    def set_categories(self, categories: list[str], selected: set[str]) -> None:
        self._selector.set_categories(categories, selected)

    def get_selected(self) -> list[str]:
        return self._selector.get_selected()

    @staticmethod
    def select_categories(
        parent: Optional[QtWidgets.QWidget],
        categories: list[str],
        selected: set[str],
    ) -> tuple[list[str], bool]:
        """Convenience: show modal dialog and return (selected, accepted)."""
        dlg = CategoryDialog(parent)
        dlg.set_categories(categories, selected)
        accepted = dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted
        return (dlg.get_selected() if accepted else sorted(selected), accepted)


# =============================================================================
# CHIP STYLING
# =============================================================================

_CHIP_QSS = f"""
    QLabel {{
        background-color: {Colors.NEUTRAL_100};
        border: 1px solid {Colors.NEUTRAL_300};
        border-radius: 10px;
        padding: 4px 10px;
        font-size: 12px;
        color: {Colors.NEUTRAL_700};
    }}
"""


# =============================================================================
# CATEGORY SUMMARY WIDGET
# =============================================================================

class CategorySummaryWidget(QtWidgets.QWidget):
    """Inline chip display showing selected categories.

    Layout:
    +-- Atrace   [Standard | 11/45] [Edit] ---------------------+
    | [am] [binder_driver] [binder_lock] [dalvik] [freq] [gfx] |
    +-----------------------------------------------------------+
    """

    select_requested = QtCore.Signal()

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        title: str = "Atrace",
    ):
        super().__init__(parent)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(Spacing.SM)

        # Header: title + status badge + action
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(Spacing.SM)

        self._title = QtWidgets.QLabel(title)
        self._title.setVisible(bool(title))
        self._title.setStyleSheet(
            f"color: {Colors.NEUTRAL_700}; font-size: 12px; font-weight: 600;"
        )
        header.addWidget(self._title)

        self._label = QtWidgets.QLabel("Standard | 11/45")
        self._label.setStyleSheet(
            f"""
            color: {Colors.PRIMARY_DARK};
            background-color: {Colors.PRIMARY_LIGHT};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 600;
            """
        )
        header.addWidget(self._label, 0, QtCore.Qt.AlignmentFlag.AlignLeft)

        self._btn = QtWidgets.QPushButton("Edit")
        self._btn.setObjectName("categorySummaryEditButton")
        self._btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._btn.setStyleSheet("padding: 4px 12px; min-height: 28px;")
        self._btn.clicked.connect(self.select_requested.emit)
        header.addWidget(self._btn)
        header.addStretch()

        outer.addLayout(header)

        # Chip summary area
        self._chip_container = QtWidgets.QWidget()
        self._chip_layout = _FlowLayout(
            self._chip_container, h_spacing=4, v_spacing=4,
        )
        self._chip_layout.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._chip_container)

    def update_summary(
        self,
        selected: list[str],
        total: int,
        preset_name: str = "",
    ) -> None:
        tag = preset_name if preset_name else "Custom"
        self._label.setText(f"{tag} | {len(selected)}/{total}")
        self._rebuild_chips(selected)

    def _rebuild_chips(self, categories: list[str]) -> None:
        # Clear existing chips
        while self._chip_layout.count():
            item = self._chip_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

        for cat in sorted(categories):
            chip = QtWidgets.QLabel(cat)
            chip.setObjectName("summaryChip")
            chip.setStyleSheet(_CHIP_QSS)
            chip.setToolTip(CATEGORY_DESCRIPTIONS.get(cat, ""))
            chip.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Maximum,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            self._chip_layout.addWidget(chip)

        self._chip_container.updateGeometry()
