"""
Category Selector Component
===========================
Grouped, filterable, collapsible category selection widget.

Features:
- Categories organized by functional groups
- Collapsible group sections
- Real-time selection counter
- Filter/search functionality
- Group-level select all / clear
- Preset quick selections
"""

from typing import Callable, Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.ui.theme import Colors, Spacing
from easy_tracer.ui.theme.stylesheet import preset_button_qss, selection_counter_qss


# =============================================================================
# CATEGORY GROUP DEFINITIONS
# =============================================================================

CATEGORY_GROUPS = {
    "Scheduling": ["sched", "freq", "idle", "irq", "workq"],
    "Graphics": ["gfx", "view", "hwui", "rs", "webview", "res"],
    "Window / Activity": ["am", "wm", "sm", "aidl"],
    "Binder": ["binder_driver", "binder_lock"],
    "Input": ["input"],
    "Memory": ["memory", "memreclaim", "dalvik"],
    "Power": ["power", "thermal", "pm"],
    "I/O": ["disk", "mmc", "sync"],
    "Audio / Video": ["audio", "video", "camera"],
    "Network": ["network"],
    "Database": ["database"],
    "Hardware": ["hal", "ss"],
}

# Reverse lookup: category -> group name
CATEGORY_TO_GROUP = {}
for group, cats in CATEGORY_GROUPS.items():
    for cat in cats:
        CATEGORY_TO_GROUP[cat] = group


# =============================================================================
# PRESETS
# =============================================================================

PRESETS = {
    "minimal": {
        "sched", "freq", "idle", "am", "wm", "view", "gfx",
        "input", "dalvik", "binder_driver", "binder_lock",
    },
    "graphics": {
        "sched", "freq", "idle", "am", "wm", "view", "gfx",
        "input", "dalvik", "binder_driver", "binder_lock",
        "webview", "res", "rs", "hwui",
    },
    "system": {
        "sched", "freq", "idle", "am", "wm", "view", "gfx",
        "input", "dalvik", "binder_driver", "binder_lock",
        "hal", "ss", "pm", "power", "thermal",
        "disk", "sync", "memory", "memreclaim",
    },
}


# =============================================================================
# CATEGORY GROUP WIDGET
# Collapsible section containing related categories
# =============================================================================

class CategoryGroupWidget(QtWidgets.QWidget):
    """A collapsible group of related categories."""

    selection_changed = QtCore.Signal()

    def __init__(
        self,
        group_name: str,
        categories: list[str],
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.group_name = group_name
        self._categories = categories
        self._checkboxes: dict[str, QtWidgets.QCheckBox] = {}
        self._expanded = True

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header row with expand/collapse and group-level controls
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        header_layout.setSpacing(Spacing.MD)

        self._expand_btn = QtWidgets.QPushButton("▼")
        self._expand_btn.setFixedWidth(24)
        self._expand_btn.setFlat(True)
        self._expand_btn.clicked.connect(self._toggle_expand)

        self._title_label = QtWidgets.QLabel(f"<b>{group_name}</b>")
        self._count_label = QtWidgets.QLabel("0/0")
        self._count_label.setStyleSheet(f"color: {Colors.NEUTRAL_500};")

        self._select_all_btn = QtWidgets.QPushButton("All")
        self._select_all_btn.setFixedWidth(40)
        self._select_all_btn.clicked.connect(self._select_all)

        self._clear_btn = QtWidgets.QPushButton("None")
        self._clear_btn.setFixedWidth(48)
        self._clear_btn.clicked.connect(self._clear_all)

        header_layout.addWidget(self._expand_btn)
        header_layout.addWidget(self._title_label)
        header_layout.addWidget(self._count_label)
        header_layout.addStretch()
        header_layout.addWidget(self._select_all_btn)
        header_layout.addWidget(self._clear_btn)

        header.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.NEUTRAL_100};
                border-bottom: 1px solid {Colors.NEUTRAL_200};
            }}
        """)

        # Content area with checkboxes
        self._content = QtWidgets.QWidget()
        content_layout = QtWidgets.QGridLayout(self._content)
        content_layout.setContentsMargins(Spacing.XL, Spacing.MD, Spacing.MD, Spacing.MD)
        content_layout.setSpacing(Spacing.SM)

        col = 0
        row = 0
        cols_per_row = 4
        for cat in sorted(categories):
            cb = QtWidgets.QCheckBox(cat)
            cb.stateChanged.connect(self._on_checkbox_changed)
            self._checkboxes[cat] = cb
            content_layout.addWidget(cb, row, col)
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1

        layout.addWidget(header)
        layout.addWidget(self._content)

        self._update_count()

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._expand_btn.setText("▼" if self._expanded else "▶")

    def _select_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
        self._update_count()
        self.selection_changed.emit()

    def _clear_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self._update_count()
        self.selection_changed.emit()

    def _on_checkbox_changed(self) -> None:
        self._update_count()
        self.selection_changed.emit()

    def _update_count(self) -> None:
        checked = sum(1 for cb in self._checkboxes.values() if cb.isChecked())
        total = len(self._checkboxes)
        self._count_label.setText(f"{checked}/{total}")

    def get_selected(self) -> list[str]:
        return [cat for cat, cb in self._checkboxes.items() if cb.isChecked()]

    def get_visible_count(self) -> tuple[int, int]:
        """Return (selected, total) for visible checkboxes."""
        visible = [cb for cb in self._checkboxes.values() if not cb.isHidden()]
        checked = sum(1 for cb in visible if cb.isChecked())
        return checked, len(visible)

    def set_selected(self, categories: set[str]) -> None:
        for cat, cb in self._checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(cat in categories)
            cb.blockSignals(False)
        self._update_count()

    def apply_filter(self, text: str) -> bool:
        """Filter checkboxes by text. Returns True if any visible."""
        needle = text.lower().strip()
        any_visible = False
        for cat, cb in self._checkboxes.items():
            match = not needle or needle in cat.lower()
            cb.setVisible(match)
            if match:
                any_visible = True
        self.setVisible(any_visible)
        return any_visible

    def has_category(self, cat: str) -> bool:
        return cat in self._checkboxes

    def set_category_checked(self, cat: str, checked: bool) -> None:
        if cat in self._checkboxes:
            self._checkboxes[cat].blockSignals(True)
            self._checkboxes[cat].setChecked(checked)
            self._checkboxes[cat].blockSignals(False)
            self._update_count()


# =============================================================================
# PRESET BUTTON GROUP
# Radio-style buttons for quick preset selection
# =============================================================================

class PresetButtonGroup(QtWidgets.QWidget):
    """Radio-style preset selector."""

    preset_selected = QtCore.Signal(str)  # Emits preset name

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._current_preset: Optional[str] = None
        self._buttons: dict[str, QtWidgets.QPushButton] = {}

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        label = QtWidgets.QLabel("Presets:")
        label.setStyleSheet(f"color: {Colors.NEUTRAL_600}; font-weight: 600;")
        layout.addWidget(label)

        presets = [
            ("minimal", "Minimal", "Core tracing: sched, freq, gfx, input, binder"),
            ("graphics", "Graphics", "Graphics analysis: adds hwui, webview, rs"),
            ("system", "System", "System analysis: adds hal, power, disk, memory"),
        ]

        for key, label_text, tooltip in presets:
            btn = QtWidgets.QPushButton(label_text)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._on_preset_clicked(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        # All / Clear buttons
        layout.addSpacing(Spacing.MD)

        self._all_btn = QtWidgets.QPushButton("All")
        self._all_btn.setToolTip("Select all categories")
        self._all_btn.clicked.connect(lambda: self.preset_selected.emit("all"))
        layout.addWidget(self._all_btn)

        self._clear_btn = QtWidgets.QPushButton("Clear")
        self._clear_btn.setToolTip("Clear all selections")
        self._clear_btn.clicked.connect(lambda: self.preset_selected.emit("clear"))
        layout.addWidget(self._clear_btn)

        layout.addStretch()

        self._update_styles()

    def _on_preset_clicked(self, preset: str) -> None:
        self._current_preset = preset
        self._update_styles()
        self.preset_selected.emit(preset)

    def _update_styles(self) -> None:
        for key, btn in self._buttons.items():
            is_selected = key == self._current_preset
            btn.setStyleSheet(preset_button_qss(is_selected))
            btn.setChecked(is_selected)

    def clear_selection(self) -> None:
        self._current_preset = None
        self._update_styles()


# =============================================================================
# MAIN CATEGORY SELECTOR WIDGET
# =============================================================================

class CategorySelector(QtWidgets.QWidget):
    """Complete category selection widget with groups, filter, and presets."""

    selection_changed = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._groups: dict[str, CategoryGroupWidget] = {}
        self._all_categories: list[str] = []
        self._ungrouped_categories: list[str] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Header row: Filter + Counter + Refresh
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(Spacing.MD)

        self._filter = QtWidgets.QLineEdit()
        self._filter.setPlaceholderText("Filter categories...")
        self._filter.textChanged.connect(self._apply_filter)
        header_layout.addWidget(self._filter, 1)

        self._counter = QtWidgets.QLabel("0 of 0")
        self._counter.setStyleSheet(selection_counter_qss())
        header_layout.addWidget(self._counter)

        self._refresh_btn = QtWidgets.QPushButton("Refresh from Device")
        self._refresh_btn.setEnabled(False)
        header_layout.addWidget(self._refresh_btn)

        layout.addWidget(header)

        # Preset row
        self._presets = PresetButtonGroup()
        self._presets.preset_selected.connect(self._apply_preset)
        layout.addWidget(self._presets)

        # Scroll area for groups
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        self._groups_container = QtWidgets.QWidget()
        self._groups_layout = QtWidgets.QVBoxLayout(self._groups_container)
        self._groups_layout.setContentsMargins(0, 0, 0, 0)
        self._groups_layout.setSpacing(0)
        self._groups_layout.addStretch()

        scroll.setWidget(self._groups_container)
        layout.addWidget(scroll, 1)

        # Ungrouped categories (shown as flat list)
        self._ungrouped_widget = CategoryGroupWidget("Other", [])
        self._ungrouped_widget.setVisible(False)
        self._ungrouped_widget.selection_changed.connect(self._on_selection_changed)

    @property
    def refresh_button(self) -> QtWidgets.QPushButton:
        """Access the refresh button for external signal connection."""
        return self._refresh_btn

    def set_categories(self, categories: list[str], default_selected: set[str]) -> None:
        """Populate the selector with available categories.

        Args:
            categories: List of category names from the device
            default_selected: Set of categories to check by default
        """
        self._all_categories = sorted(categories)

        # Clear existing groups
        for group in self._groups.values():
            group.deleteLater()
        self._groups.clear()

        # Categorize
        grouped: dict[str, list[str]] = {g: [] for g in CATEGORY_GROUPS}
        ungrouped: list[str] = []

        for cat in self._all_categories:
            group = CATEGORY_TO_GROUP.get(cat)
            if group:
                grouped[group].append(cat)
            else:
                ungrouped.append(cat)

        self._ungrouped_categories = ungrouped

        # Create group widgets (only for groups that have categories)
        insert_idx = 0
        for group_name in CATEGORY_GROUPS:
            cats = grouped.get(group_name, [])
            if not cats:
                continue
            widget = CategoryGroupWidget(group_name, cats)
            widget.selection_changed.connect(self._on_selection_changed)
            widget.set_selected(default_selected)
            self._groups[group_name] = widget
            self._groups_layout.insertWidget(insert_idx, widget)
            insert_idx += 1

        # Handle ungrouped
        if ungrouped:
            self._ungrouped_widget.deleteLater()
            self._ungrouped_widget = CategoryGroupWidget("Other", ungrouped)
            self._ungrouped_widget.selection_changed.connect(self._on_selection_changed)
            self._ungrouped_widget.set_selected(default_selected)
            self._groups["Other"] = self._ungrouped_widget
            self._groups_layout.insertWidget(insert_idx, self._ungrouped_widget)

        self._update_counter()

    def get_selected(self) -> list[str]:
        """Return list of all selected category names."""
        result = []
        for group in self._groups.values():
            result.extend(group.get_selected())
        return result

    def set_selected(self, categories: set[str]) -> None:
        """Set selection state for all categories."""
        for group in self._groups.values():
            group.set_selected(categories)
        self._presets.clear_selection()
        self._update_counter()

    def _apply_filter(self, text: str) -> None:
        for group in self._groups.values():
            group.apply_filter(text)

    def _apply_preset(self, preset: str) -> None:
        if preset == "all":
            self.set_selected(set(self._all_categories))
        elif preset == "clear":
            self.set_selected(set())
        elif preset in PRESETS:
            self.set_selected(PRESETS[preset])
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        self._update_counter()
        self._presets.clear_selection()
        self.selection_changed.emit()

    def _update_counter(self) -> None:
        selected = len(self.get_selected())
        total = len(self._all_categories)
        self._counter.setText(f"{selected} of {total}")

    def clear(self) -> None:
        """Clear all categories (device disconnected)."""
        for group in self._groups.values():
            group.deleteLater()
        self._groups.clear()
        self._all_categories.clear()
        self._ungrouped_categories.clear()
        self._counter.setText("0 of 0")
