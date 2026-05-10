"""Perfetto-specific control widgets shared by the Perfetto panel."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from easy_tracer.models.category_registry import detect_preset_name
from easy_tracer.ui.dialogs.category_dialog import CategorySummaryWidget
from easy_tracer.ui.panels.app_targets import (
    APP_TARGET_OPTIONS,
    CUSTOM_PACKAGE_TARGET,
    resolve_atrace_apps,
)
from easy_tracer.ui.theme import Colors, Spacing


SOURCE_PRESET_ENABLED: dict[str, set[str]] = {
    "standard": {"ftrace", "process_stats"},
    "graphics": {"ftrace", "process_stats", "surfaceflinger", "gpu_memory"},
    "memory": {"ftrace", "process_stats", "sys_stats"},
    "full": {
        "ftrace",
        "process_stats",
        "sys_stats",
        "system_info",
        "surfaceflinger",
        "gpu_memory",
        "packages_list",
        "android_log",
    },
}
DEFAULT_SOURCE_PRESET = "standard"

DATA_SOURCE_SECTIONS: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...] = (
    (
        "Core",
        (
            ("ftrace", "Ftrace", "CPU scheduling and low-level system events."),
            ("process_stats", "Process Stats", "Per-process CPU and memory snapshots."),
        ),
    ),
    (
        "Graphics",
        (
            (
                "surfaceflinger",
                "SurfaceFlinger",
                "Android frame timeline and compositor events.",
            ),
            ("gpu_memory", "GPU Memory", "GPU memory usage counters."),
        ),
    ),
    (
        "Memory",
        (("sys_stats", "Sys Stats", "System-wide memory counters."),),
    ),
    (
        "System",
        (
            ("system_info", "System Info", "Kernel, CPU, and device metadata."),
            ("packages_list", "Packages List", "Installed packages metadata."),
            ("android_log", "Android Log", "Logcat stream inside the trace."),
        ),
    ),
)

_SOURCE_GRID_COLUMNS = 2


class PerfettoDataSourceTabs(QtWidgets.QTabWidget):
    """Tabbed editor for Perfetto data-source toggles."""

    def __init__(
        self,
        sections: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sections = sections
        self._checkboxes: dict[str, QtWidgets.QCheckBox] = {}

        self.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.tabBar().setUsesScrollButtons(False)
        self.tabBar().setElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.tabBar().setExpanding(False)

        for section_title, items in sections:
            tab_index = self.addTab(self._build_tab(items), section_title)
            self.setTabToolTip(tab_index, ", ".join(label for _, label, _ in items))

        self._update_tab_counts()

    @property
    def checkboxes(self) -> dict[str, QtWidgets.QCheckBox]:
        return self._checkboxes

    def checkbox(self, key: str) -> QtWidgets.QCheckBox:
        return self._checkboxes[key]

    def is_enabled(self, key: str) -> bool:
        return self._checkboxes[key].isChecked()

    def selected_keys(self) -> set[str]:
        return {key for key, checkbox in self._checkboxes.items() if checkbox.isChecked()}

    def set_enabled_keys(self, enabled: set[str]) -> None:
        for key, checkbox in self._checkboxes.items():
            checkbox.setChecked(key in enabled)
        self._update_tab_counts()

    def _build_tab(
        self,
        items: tuple[tuple[str, str, str], ...],
    ) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(widget)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setHorizontalSpacing(Spacing.XL)
        layout.setVerticalSpacing(Spacing.SM)

        for index, (key, label, tooltip) in enumerate(items):
            checkbox = QtWidgets.QCheckBox(label)
            checkbox.setToolTip(tooltip)
            checkbox.toggled.connect(self._update_tab_counts)
            self._checkboxes[key] = checkbox
            layout.addWidget(
                checkbox,
                index // _SOURCE_GRID_COLUMNS,
                index % _SOURCE_GRID_COLUMNS,
            )

        layout.setColumnStretch(_SOURCE_GRID_COLUMNS, 1)
        layout.setRowStretch((len(items) + _SOURCE_GRID_COLUMNS - 1) // _SOURCE_GRID_COLUMNS, 1)
        return widget

    def _update_tab_counts(self) -> None:
        for index, (title, items) in enumerate(self._sections):
            enabled = sum(
                1 for key, _label, _tooltip in items if self._checkboxes[key].isChecked()
            )
            self.setTabText(index, f"{title} ({enabled}/{len(items)})")


class AtraceScopeEditor(QtWidgets.QWidget):
    """Category and app-scope editor for Perfetto atrace config."""

    category_edit_requested = QtCore.Signal()

    def __init__(
        self,
        selected_categories: list[str],
        total_categories: int,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._selected_categories = list(selected_categories)
        self._total_categories = total_categories

        self.header_row = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(self.header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(Spacing.LG)

        self.category_summary = CategorySummaryWidget(
            title="Categories",
            max_visible_chips=None,
        )
        self.category_summary.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.category_summary.select_requested.connect(self.category_edit_requested.emit)
        header_layout.addWidget(self.category_summary, 1)

        self.app_widget = self._build_app_scope()
        header_layout.addWidget(self.app_widget, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header_row)

        self._update_category_summary()

    def selected_categories(self) -> list[str]:
        return list(self._selected_categories)

    def selected_apps(self) -> list[str]:
        return resolve_atrace_apps(
            self.target_combo.currentText(),
            self.custom_target.text(),
        )

    def set_categories(
        self,
        categories: list[str],
        total_categories: int | None = None,
    ) -> None:
        self._selected_categories = list(categories)
        if total_categories is not None:
            self._total_categories = total_categories
        self._update_category_summary()

    def sync_custom_target(self, text: str) -> None:
        is_custom = text == CUSTOM_PACKAGE_TARGET
        self.custom_target.setEnabled(is_custom)
        self.custom_target.setVisible(is_custom)
        self.updateGeometry()

    def _build_app_scope(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)

        app_scope_label = QtWidgets.QLabel("Apps")
        app_scope_label.setStyleSheet(
            f"color: {Colors.NEUTRAL_700}; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(app_scope_label)

        controls = QtWidgets.QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(Spacing.SM)

        self.target_combo = QtWidgets.QComboBox()
        self._configure_compact_combo(self.target_combo, 12)
        self.target_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.target_combo.addItems(APP_TARGET_OPTIONS)
        self.target_combo.currentTextChanged.connect(self.sync_custom_target)
        controls.addWidget(self.target_combo)

        self.custom_target = QtWidgets.QLineEdit()
        self.custom_target.setPlaceholderText("com.example.app")
        self.custom_target.setEnabled(False)
        self.custom_target.setVisible(False)
        self.custom_target.setMinimumWidth(160)
        self.custom_target.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        controls.addWidget(self.custom_target, 1)

        layout.addLayout(controls)
        return widget

    def _update_category_summary(self) -> None:
        preset_name = detect_preset_name(set(self._selected_categories))
        self.category_summary.update_summary(
            self._selected_categories,
            self._total_categories,
            preset_name,
        )

    def _configure_compact_combo(
        self,
        combo: QtWidgets.QComboBox,
        minimum_contents_length: int,
    ) -> None:
        combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(minimum_contents_length)
