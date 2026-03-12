"""Flat, filterable widget for choosing atrace categories."""

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from easy_tracer.models.category_registry import (
    ATRACE_PRESETS,
    CATEGORY_DESCRIPTIONS,
    PRESET_ORDER,
    detect_preset_name,
)
from easy_tracer.ui.theme import Colors, Spacing
from easy_tracer.ui.theme.stylesheet import selection_counter_qss


# =============================================================================
# PRESET BUTTON GROUP
# =============================================================================

class PresetButtonGroup(QtWidgets.QWidget):
    """Compact preset selector using pill-style buttons."""

    preset_selected = QtCore.Signal(str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._buttons: dict[str, QtWidgets.QToolButton] = {}

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        layout.setSpacing(Spacing.XS)

        label = QtWidgets.QLabel("Presets:")
        label.setStyleSheet(f"color: {Colors.NEUTRAL_600}; font-size: 12px;")
        layout.addWidget(label)

        presets = [
            (key, key.capitalize(), f"{len(ATRACE_PRESETS[key])} categories")
            for key in PRESET_ORDER
        ]

        for key, label_text, tooltip in presets:
            btn = QtWidgets.QToolButton()
            btn.setText(label_text)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_preset_clicked(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addSpacing(Spacing.SM)

        self._all_btn = QtWidgets.QToolButton()
        self._all_btn.setText("Select All")
        self._all_btn.setCheckable(True)
        self._all_btn.clicked.connect(lambda: self.preset_selected.emit("all"))
        layout.addWidget(self._all_btn)

        self._clear_btn = QtWidgets.QToolButton()
        self._clear_btn.setText("Clear All")
        self._clear_btn.setCheckable(True)
        self._clear_btn.clicked.connect(lambda: self.preset_selected.emit("clear"))
        layout.addWidget(self._clear_btn)

        layout.addStretch()

        self._apply_pill_style()

    def _apply_pill_style(self) -> None:
        base_style = f"""
            QToolButton {{
                background-color: {Colors.NEUTRAL_100};
                border: 1px solid {Colors.NEUTRAL_300};
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                color: {Colors.NEUTRAL_700};
            }}
            QToolButton:hover {{
                background-color: {Colors.NEUTRAL_200};
            }}
            QToolButton:checked {{
                background-color: {Colors.PRIMARY};
                border-color: {Colors.PRIMARY_DARK};
                color: {Colors.ON_PRIMARY};
            }}
        """
        for btn in self._buttons.values():
            btn.setStyleSheet(base_style)
        
        # Action buttons style (not checkable)
        action_style = f"""
            QToolButton {{
                background-color: transparent;
                border: 1px solid {Colors.NEUTRAL_300};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                color: {Colors.NEUTRAL_700};
            }}
            QToolButton:hover {{
                background-color: {Colors.NEUTRAL_200};
            }}
            QToolButton:pressed {{
                background-color: {Colors.NEUTRAL_300};
            }}
            QToolButton:checked {{
                background-color: {Colors.PRIMARY_LIGHT};
                border-color: {Colors.PRIMARY};
                color: {Colors.NEUTRAL_900};
                font-weight: 600;
            }}
        """
        self._all_btn.setStyleSheet(action_style)
        self._clear_btn.setStyleSheet(action_style)

    def _on_preset_clicked(self, preset: str) -> None:
        # Uncheck other preset buttons (radio behavior)
        for key, btn in self._buttons.items():
            btn.setChecked(key == preset)
        self.preset_selected.emit(preset)

    def clear_selection(self) -> None:
        self.set_selected(None)

    def set_selected(self, preset: Optional[str]) -> None:
        """Updates the active preset button without emitting signals."""

        for btn in self._buttons.values():
            btn.setChecked(False)
        self._all_btn.setChecked(False)
        self._clear_btn.setChecked(False)
        if preset in self._buttons:
            self._buttons[preset].setChecked(True)
        elif preset == "all":
            self._all_btn.setChecked(True)
        elif preset == "clear":
            self._clear_btn.setChecked(True)


# =============================================================================
# CATEGORY ITEM WIDGET
# =============================================================================

class CategoryItemWidget(QtWidgets.QWidget):
    """A single category item with checkbox, name, and description."""

    state_changed = QtCore.Signal()

    def __init__(
        self,
        name: str,
        description: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.name = name
        self.description = description

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)
        layout.setSpacing(Spacing.MD)

        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.checkbox.stateChanged.connect(self._on_state_changed)
        layout.addWidget(self.checkbox)

        self.name_label = QtWidgets.QLabel(name)
        self.name_label.setStyleSheet(f"font-weight: bold; color: {Colors.NEUTRAL_800};")
        self.name_label.setFixedWidth(100)
        layout.addWidget(self.name_label)

        self.desc_label = QtWidgets.QLabel(description)
        self.desc_label.setStyleSheet(f"color: {Colors.NEUTRAL_600};")
        self.desc_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        layout.addWidget(self.desc_label)

        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
        super().mouseReleaseEvent(event)

    def _on_state_changed(self) -> None:
        self.state_changed.emit()

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(checked)
        self.checkbox.blockSignals(False)

    def matches_filter(self, text: str) -> bool:
        needle = text.lower().strip()
        if not needle:
            return True
        return needle in self.name.lower() or needle in self.description.lower()


# =============================================================================
# MAIN CATEGORY SELECTOR WIDGET
# =============================================================================

class CategorySelector(QtWidgets.QWidget):
    """Complete category selection widget with dual-column list and presets.

    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │ [Filter options...] (12 of 45)      [Refresh from Device]   │
    │ Presets: (Minimal) (Graphics) (System) [Select All] [Clear] │
    ├────────────────────────────┬────────────────────────────────┤
    │ ☑ adb        ADB           │ ☐ mmc        eMMC commands     │
    │ ☐ am         Activity Mgr  │ ☑ network    Network           │
    │ ☑ gfx        Graphics      │ ☐ pm         Power Management  │
    │ ☐ view       View System   │ ☐ sched      CPU Scheduling    │
    └────────────────────────────┴────────────────────────────────┘
    """

    selection_changed = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._items: dict[str, CategoryItemWidget] = {}
        self._all_categories: list[str] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Header row: Filter + Counter + Refresh
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(Spacing.SM)

        self._filter = QtWidgets.QLineEdit()
        self._filter.setPlaceholderText("Filter options...")
        self._filter.setMaximumWidth(250)
        self._filter.textChanged.connect(self._apply_filter)
        header_layout.addWidget(self._filter)

        self._counter = QtWidgets.QLabel("0 of 0")
        self._counter.setStyleSheet(selection_counter_qss())
        header_layout.addWidget(self._counter)

        header_layout.addStretch()

        self._refresh_btn = QtWidgets.QPushButton("Refresh from Device")
        self._refresh_btn.setEnabled(False)
        header_layout.addWidget(self._refresh_btn)

        layout.addWidget(header)

        # Preset row
        self._presets = PresetButtonGroup()
        self._presets.preset_selected.connect(self._apply_preset)
        layout.addWidget(self._presets)

        # Scroll area for dual-column list
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.NEUTRAL_300};
                border-radius: 4px;
            }}
        """)

        self._list_container = QtWidgets.QWidget()
        self._list_container.setStyleSheet("background-color: transparent;")

        # Dual-column layout using QHBoxLayout with two QVBoxLayouts
        self._columns_layout = QtWidgets.QHBoxLayout(self._list_container)
        self._columns_layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        self._columns_layout.setSpacing(Spacing.MD)

        self._left_column = QtWidgets.QVBoxLayout()
        self._left_column.setSpacing(0)
        self._left_column.addStretch()

        self._right_column = QtWidgets.QVBoxLayout()
        self._right_column.setSpacing(0)
        self._right_column.addStretch()

        self._columns_layout.addLayout(self._left_column, 1)
        self._columns_layout.addLayout(self._right_column, 1)

        self._scroll.setWidget(self._list_container)
        layout.addWidget(self._scroll, 1)

    @property
    def refresh_button(self) -> QtWidgets.QPushButton:
        """Access the refresh button for external signal connection."""
        return self._refresh_btn

    def _add_category_to_column(
        self,
        cat: str,
        column: QtWidgets.QVBoxLayout,
        default_selected: set[str],
    ) -> None:
        """Create and add a category item widget to the specified column."""
        desc = CATEGORY_DESCRIPTIONS.get(cat, "")
        item_widget = CategoryItemWidget(cat, desc)
        item_widget.setChecked(cat in default_selected)
        item_widget.state_changed.connect(self._on_selection_changed)
        self._items[cat] = item_widget
        column.insertWidget(column.count() - 1, item_widget)

    def set_categories(self, categories: list[str], default_selected: set[str]) -> None:
        """Populate the selector with available categories in dual-column layout.

        Args:
            categories: List of category names from the device
            default_selected: Set of categories to check by default
        """
        self._all_categories = sorted(categories)

        self._clear_items()
        self._clear_column(self._left_column)
        self._clear_column(self._right_column)

        mid = (len(self._all_categories) + 1) // 2

        for cat in self._all_categories[:mid]:
            self._add_category_to_column(cat, self._left_column, default_selected)

        for cat in self._all_categories[mid:]:
            self._add_category_to_column(cat, self._right_column, default_selected)

        self._apply_filter(self._filter.text())
        self._sync_preset_state()
        self._update_counter()

    def _clear_column(self, column: QtWidgets.QVBoxLayout) -> None:
        """Remove all widgets from a column layout except the stretch."""
        while column.count() > 0:
            item = column.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            del item
        column.addStretch()

    def _clear_items(self) -> None:
        """Delete all category widgets and reset the item lookup."""
        for item in self._items.values():
            item.deleteLater()
        self._items.clear()

    def get_selected(self) -> list[str]:
        """Return list of all selected category names."""
        return [cat for cat, item in self._items.items() if item.isChecked()]

    def set_selected(self, categories: set[str]) -> None:
        """Set selection state for all categories."""
        for cat, item in self._items.items():
            item.setChecked(cat in categories)
        self._sync_preset_state()
        self._update_counter()

    def _apply_filter(self, text: str) -> None:
        for item in self._items.values():
            item.setVisible(item.matches_filter(text))

    def _apply_preset(self, preset: str) -> None:
        if preset == "all":
            self.set_selected(set(self._all_categories))
        elif preset == "clear":
            self.set_selected(set())
        elif preset in ATRACE_PRESETS:
            self.set_selected(set(ATRACE_PRESETS[preset]))
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        self._update_counter()
        self._sync_preset_state()
        self.selection_changed.emit()

    def _matched_preset(self, selected: set[str]) -> Optional[str]:
        """Return the matching preset key for the current selection."""
        # "all" and "clear" are local UI states, not registry presets.
        if self._all_categories and selected == set(self._all_categories):
            return "all"
        if self._all_categories and not selected:
            return "clear"

        preset_name = detect_preset_name(selected)
        return preset_name.lower() if preset_name else None

    def _sync_preset_state(self) -> None:
        selected = set(self.get_selected())
        self._presets.set_selected(self._matched_preset(selected))

    def _update_counter(self) -> None:
        selected = len(self.get_selected())
        total = len(self._all_categories)
        self._counter.setText(f"{selected} of {total}")

    def clear(self) -> None:
        """Clear all categories (device disconnected)."""
        self._clear_items()
        self._all_categories.clear()
        self._clear_column(self._left_column)
        self._clear_column(self._right_column)
        self._presets.clear_selection()
        self._counter.setText("0 of 0")
        self._filter.clear()
