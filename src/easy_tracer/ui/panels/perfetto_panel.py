"""
Perfetto Panel
==============
Configuration and control panel for Perfetto trace recording.

Features:
- Preset-based configuration (Standard, Graphics, Memory, Full, Custom)
- Preset-first data source layout with custom editor
- Atrace category selection via modal dialog (unified registry)
- Auxiliary output options
"""

import os
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets
from easy_tracer.framework.perfetto_config_builder import PerfettoConfig
from easy_tracer.models.category_registry import (
    CATEGORY_DESCRIPTIONS,
    ATRACE_PRESETS,
    detect_preset_name,
)
from easy_tracer.models.requests import PerfettoRequest
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.components.cards import ResultCard
from easy_tracer.ui.dialogs.category_dialog import CategoryDialog, CategorySummaryWidget
from easy_tracer.ui.panels.app_targets import (
    APP_TARGET_OPTIONS,
    CUSTOM_PACKAGE_TARGET,
    resolve_atrace_apps,
)
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog
from easy_tracer.ui.theme import Colors, Spacing


# =============================================================================
# PERFETTO DATA SOURCE PRESETS (Perfetto-specific, NOT atrace)
# =============================================================================

_DS_ENABLED: dict[str, set[str]] = {
    "standard": {"ftrace", "process_stats"},
    "graphics": {"ftrace", "process_stats", "surfaceflinger", "gpu_memory"},
    "memory":   {"ftrace", "process_stats", "sys_stats"},
    "full":     {
        "ftrace", "process_stats", "sys_stats", "system_info",
        "surfaceflinger", "gpu_memory", "packages_list", "android_log",
    },
}

_DATA_SOURCE_SECTIONS: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...] = (
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
            ("surfaceflinger", "SurfaceFlinger", "Android frame timeline and compositor events."),
            ("gpu_memory", "GPU Memory", "GPU memory usage counters."),
        ),
    ),
    (
        "Memory",
        (
            ("sys_stats", "Sys Stats", "System-wide memory counters."),
        ),
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
_DATA_SOURCE_LABELS = {
    key: label
    for _section, items in _DATA_SOURCE_SECTIONS
    for key, label, _tooltip in items
}

class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class PerfettoSettingsDialog(BaseSettingsDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, "Perfetto Settings")

        self.buffer_combo = QtWidgets.QComboBox()
        self.buffer_combo.addItems(["32 MB", "64 MB", "150 MB", "300 MB"])
        self.buffer_combo.setCurrentIndex(2)  # 150 MB default
        self.add_row("Buffer Size:", self.buffer_combo)

        self.write_period = QtWidgets.QSpinBox()
        self.write_period.setRange(500, 10000)
        self.write_period.setValue(2500)
        self.write_period.setSuffix(" ms")
        self.add_row("Write Period:", self.write_period)

        self.flush_period = QtWidgets.QSpinBox()
        self.flush_period.setRange(1000, 60000)
        self.flush_period.setValue(30000)
        self.flush_period.setSuffix(" ms")
        self.add_row("Flush Period:", self.flush_period)


class PerfettoPanel(BasePanel):
    """Perfetto trace recording panel.

    Layout:
    +-- CAPTURE SETTINGS -------------------------------------------+
    | Duration: [10s v]  Mode: (Normal) (Long)                      |
    | Output: [...output...]  [dir]  [Settings]                     |
    | PRESETS: (Standard) (Graphics) (Memory) (Full) (Custom)       |
    +---------------------------------------------------------------+
    +-- DATA SOURCES -----------------------------------------------+
    | Included: Ftrace, Process Stats, SurfaceFlinger               |
    | [Core] [Graphics] [Memory] [System] editor only in Custom     |
    +---------------------------------------------------------------+
    +-- ATRACE -----------------------------------------------------+
    | Categories [Standard | 11/43] [Edit]                         |
    | [am] [binder_driver] [binder_lock] [dalvik] [freq] [gfx]     |
    | Apps: [All Apps (*) v]                                       |
    | Package: [com.example.app_______________________________]     |
    +---------------------------------------------------------------+
    """

    def __init__(self, presenter: PerfettoPresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._auxiliary_options: dict[str, bool] = {}
        self._current_preset: str = "standard"
        self._atrace_categories: list[str] = list(ATRACE_PRESETS["standard"])
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self._setup_ui()
        self.update_device(self.device_serial)

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.MD)

        # =====================================================================
        # CAPTURE SETTINGS GROUP
        # =====================================================================
        settings_group = QtWidgets.QGroupBox("Capture Settings")
        settings_layout = QtWidgets.QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        settings_layout.setSpacing(Spacing.SM)

        # Row 1: Duration, Mode
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(Spacing.LG)

        row1.addWidget(QtWidgets.QLabel("Duration:"))
        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "10s", "30s", "60s", "5min", "10min"])
        self.duration_combo.setCurrentIndex(1)  # 10s default
        row1.addWidget(self.duration_combo)

        row1.addWidget(QtWidgets.QLabel("Mode:"))
        self.normal_radio = QtWidgets.QRadioButton("Normal")
        self.long_radio = QtWidgets.QRadioButton("Long")
        self.normal_radio.setChecked(True)
        row1.addWidget(self.normal_radio)
        row1.addWidget(self.long_radio)

        row1.addStretch()
        settings_layout.addLayout(row1)

        # Row 2: Output path
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(Spacing.SM)

        row2.addWidget(QtWidgets.QLabel("Output:"))
        self.output_path = OutputPathWidget(
            self.default_output_dir,
            label="",
            editable=True,
            tooltip="Shared output directory. Changes sync across panels.",
        )
        row2.addWidget(self.output_path, 1)

        self.open_output_btn = QtWidgets.QPushButton()
        self.open_output_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        self.open_output_btn.setToolTip("Open output directory")
        self.open_output_btn.setMaximumWidth(36)
        self.open_output_btn.clicked.connect(self._on_open_output)
        row2.addWidget(self.open_output_btn)

        self.settings_dialog = PerfettoSettingsDialog(self)
        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self.settings_dialog.exec)
        row2.addWidget(self.settings_btn)

        settings_layout.addLayout(row2)

        # Row 3: Presets
        preset_layout = QtWidgets.QHBoxLayout()
        preset_layout.setSpacing(Spacing.SM)
        preset_layout.addWidget(QtWidgets.QLabel("Presets:"))

        self.preset_group = QtWidgets.QButtonGroup(self)
        self._standard_preset_btn: Optional[QtWidgets.QRadioButton] = None
        presets = [
            ("standard", "Standard", "Basic CPU scheduling and atrace"),
            ("graphics", "Graphics", "Standard + SurfaceFlinger + GPU"),
            ("memory", "Memory", "Standard + memory tracking"),
            ("full", "Full", "All data sources"),
            ("custom", "Custom", "Manual configuration"),
        ]
        for preset_id, label, tooltip in presets:
            btn = QtWidgets.QRadioButton(label)
            btn.setToolTip(tooltip)
            btn.setProperty("preset_id", preset_id)
            self.preset_group.addButton(btn)
            preset_layout.addWidget(btn)
            if preset_id == "standard":
                self._standard_preset_btn = btn

        preset_layout.addStretch()
        settings_layout.addLayout(preset_layout)

        layout.addWidget(settings_group)

        # =====================================================================
        # DATA SOURCES GROUP
        # =====================================================================
        sources_group = QtWidgets.QGroupBox("Data Sources")
        self.sources_group = sources_group
        sources_layout = QtWidgets.QVBoxLayout(sources_group)
        sources_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        sources_layout.setSpacing(Spacing.MD)

        self.source_summary_widget = QtWidgets.QWidget()
        source_summary_layout = QtWidgets.QVBoxLayout(self.source_summary_widget)
        source_summary_layout.setContentsMargins(0, 0, 0, 0)
        source_summary_layout.setSpacing(Spacing.XS)

        source_summary_label = QtWidgets.QLabel("Included")
        source_summary_label.setStyleSheet(
            f"color: {Colors.NEUTRAL_700}; font-size: 12px; font-weight: 600;"
        )
        source_summary_layout.addWidget(source_summary_label)

        self.source_summary_value = QtWidgets.QLabel()
        self.source_summary_value.setWordWrap(True)
        self.source_summary_value.setStyleSheet(
            f"color: {Colors.NEUTRAL_700}; line-height: 1.4;"
        )
        source_summary_layout.addWidget(self.source_summary_value)
        sources_layout.addWidget(self.source_summary_widget)

        self.sources_editor_widget = QtWidgets.QWidget()
        sources_editor_layout = QtWidgets.QGridLayout(self.sources_editor_widget)
        sources_editor_layout.setContentsMargins(0, 0, 0, 0)
        sources_editor_layout.setHorizontalSpacing(Spacing.LG)
        sources_editor_layout.setVerticalSpacing(Spacing.MD)

        self._ds_map: dict[str, QtWidgets.QCheckBox] = {}
        for index, (section_title, items) in enumerate(_DATA_SOURCE_SECTIONS):
            section = self._build_source_section(section_title, items)
            sources_editor_layout.addWidget(section, index // 2, index % 2)

        sources_layout.addWidget(self.sources_editor_widget)

        layout.addWidget(sources_group)

        # =====================================================================
        # ATRACE GROUP (category summary + app scope)
        # =====================================================================
        atrace_group = QtWidgets.QGroupBox("Atrace")
        self.atrace_group = atrace_group
        atrace_layout = QtWidgets.QVBoxLayout(atrace_group)
        atrace_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        atrace_layout.setSpacing(Spacing.MD)

        self._category_summary = CategorySummaryWidget(title="Categories")
        self._category_summary.select_requested.connect(self._on_select_atrace)
        atrace_layout.addWidget(self._category_summary)

        app_scope_row = QtWidgets.QHBoxLayout()
        app_scope_row.setSpacing(Spacing.SM)
        app_scope_row.addWidget(QtWidgets.QLabel("Apps:"))

        self.atrace_target_combo = QtWidgets.QComboBox()
        self._configure_compact_combo(self.atrace_target_combo, 12)
        self.atrace_target_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.atrace_target_combo.addItems(APP_TARGET_OPTIONS)
        self.atrace_target_combo.currentTextChanged.connect(self._toggle_custom_target)
        app_scope_row.addWidget(self.atrace_target_combo)
        app_scope_row.addStretch(1)
        atrace_layout.addLayout(app_scope_row)

        self.atrace_custom_target = QtWidgets.QLineEdit()
        self.atrace_custom_target.setPlaceholderText("com.example.app")
        self.atrace_custom_target.setEnabled(False)
        self.atrace_custom_target.setVisible(False)
        self.atrace_custom_target.setMinimumWidth(280)
        self.atrace_custom_target.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        self.atrace_custom_target_row = self._build_detail_row(
            "Package:",
            self.atrace_custom_target,
        )
        self.atrace_custom_target_row.setVisible(False)
        atrace_layout.addWidget(self.atrace_custom_target_row)

        layout.addWidget(atrace_group)

        # =====================================================================
        # RESULT CARD
        # =====================================================================
        self.result_card = ResultCard()
        self.result_card.open_output_clicked.connect(self._on_open_output)
        self.result_card.view_trace_clicked.connect(self._on_view_in_perfetto)
        layout.addWidget(self.result_card)

        # Connect preset buttons AFTER all UI is created
        for btn in self.preset_group.buttons():
            preset_id = btn.property("preset_id")
            btn.toggled.connect(lambda checked, p=preset_id: self._on_preset_toggled(checked, p))

        # Set default preset and apply it
        if self._standard_preset_btn:
            self._standard_preset_btn.setChecked(True)
        self._apply_preset("standard")

    # =========================================================================
    # UI HELPERS
    # =========================================================================

    def _configure_compact_combo(
        self,
        combo: QtWidgets.QComboBox,
        minimum_contents_length: int,
    ) -> None:
        combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(minimum_contents_length)

    def _build_detail_row(
        self,
        label_text: str,
        field: QtWidgets.QWidget,
    ) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.SM)
        layout.addWidget(QtWidgets.QLabel(label_text))
        layout.addWidget(field, 1)
        return row

    def _build_source_section(
        self,
        title: str,
        items: tuple[tuple[str, str, str], ...],
    ) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)

        header = QtWidgets.QLabel(title)
        header.setStyleSheet(
            f"color: {Colors.NEUTRAL_700}; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(header)

        for key, label, tooltip in items:
            checkbox = QtWidgets.QCheckBox(label)
            checkbox.setToolTip(tooltip)
            checkbox.toggled.connect(self._update_source_summary)
            setattr(self, f"ds_{key}", checkbox)
            self._ds_map[key] = checkbox
            layout.addWidget(checkbox)

        layout.addStretch(1)
        return widget

    # =========================================================================
    # PRESET APPLICATION
    # =========================================================================

    def _on_preset_toggled(self, checked: bool, preset_id: str) -> None:
        if checked:
            self._apply_preset(preset_id)

    def _apply_preset(self, preset_id: str) -> None:
        """Apply preset: data sources (local) + atrace (from registry)."""
        self._current_preset = preset_id
        if preset_id == "custom":
            self._sync_sources_visibility()
            return

        # Data sources (Perfetto-specific concern)
        enabled = _DS_ENABLED.get(preset_id, _DS_ENABLED["standard"])
        for key, cb in self._ds_map.items():
            cb.setChecked(key in enabled)

        # Atrace categories (unified registry)
        self._atrace_categories = list(
            ATRACE_PRESETS.get(preset_id, ATRACE_PRESETS["standard"])
        )
        self._update_category_summary()
        self._sync_sources_visibility()

    # =========================================================================
    # ATRACE CATEGORY SELECTION
    # =========================================================================

    def _on_select_atrace(self) -> None:
        """Open the category dialog and apply user selection."""
        all_cats = sorted(CATEGORY_DESCRIPTIONS.keys())
        selected, accepted = CategoryDialog.select_categories(
            self, all_cats, set(self._atrace_categories),
        )
        if accepted:
            self._atrace_categories = selected
            self._update_category_summary()

    def _update_category_summary(self) -> None:
        preset_name = detect_preset_name(set(self._atrace_categories))
        self._category_summary.update_summary(
            self._atrace_categories, len(CATEGORY_DESCRIPTIONS), preset_name,
        )

    def _selected_atrace_categories(self) -> list[str]:
        return list(self._atrace_categories)

    def _toggle_custom_target(self, text: str) -> None:
        is_custom = text == CUSTOM_PACKAGE_TARGET
        self.atrace_custom_target.setEnabled(is_custom)
        self.atrace_custom_target.setVisible(is_custom)
        self.atrace_custom_target_row.setVisible(is_custom)
        self.updateGeometry()

    def _sync_sources_visibility(self) -> None:
        is_custom = self._current_preset == "custom"
        self.source_summary_widget.setVisible(not is_custom)
        self.sources_editor_widget.setVisible(is_custom)
        self._update_source_summary()

    def _update_source_summary(self) -> None:
        enabled = [
            _DATA_SOURCE_LABELS[key]
            for key, cb in self._ds_map.items()
            if cb.isChecked()
        ]
        self.source_summary_value.setText(
            ", ".join(enabled) if enabled else "No data sources selected."
        )

    def _selected_atrace_apps(self) -> list[str]:
        return resolve_atrace_apps(
            self.atrace_target_combo.currentText(),
            self.atrace_custom_target.text(),
        )

    # =========================================================================
    # AUXILIARY / NAVIGATION
    # =========================================================================

    def set_auxiliary_options(self, options: dict[str, bool]) -> None:
        """Set auxiliary output options from main window."""
        self._auxiliary_options = options

    def _on_open_output(self) -> None:
        output_dir = self.output_path.output_dir()
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(output_dir))

    def _on_view_in_perfetto(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://ui.perfetto.dev"))

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        self.readiness_changed.emit(self.is_ready())
        if serial:
            self.status_message.emit(f"Selected device: {serial}")
        else:
            self.status_message.emit("Please select a device.")

    def is_ready(self) -> bool:
        return bool(self.device_serial) and not self.presenter.is_recording

    def update_view(self) -> None:
        busy = self.presenter.is_recording
        self.busy_changed.emit(busy)
        self.readiness_changed.emit(self.is_ready())

        if busy:
            self.result_card.clear()
            self.status_message.emit("Recording trace... Please wait.")
        else:
            self.status_message.emit("Ready.")

        if self.presenter.error_message:
            self.error_message.emit(self.presenter.error_message)
        elif self.presenter.last_output_path:
            self.status_message.emit(f"Trace saved to: {self.presenter.last_output_path}")
            self._show_result_card()

    # =========================================================================
    # CAPTURE CONTROL
    # =========================================================================

    def _duration_seconds(self) -> int:
        text = self.duration_combo.currentText()
        if text.endswith("min"):
            return int(text.replace("min", "")) * 60
        return int(text.replace("s", ""))

    def _buffer_kb(self) -> int:
        text = self.settings_dialog.buffer_combo.currentText().replace("MB", "").strip()
        return int(text) * 1024

    def _build_custom_config(
        self,
        duration_seconds: int,
        buffer_size_kb: int,
        categories: list[str],
        atrace_apps: list[str],
    ) -> PerfettoConfig:
        """Build the explicit config used for the custom preset."""
        # Custom mode bypasses registry presets and mirrors the live checkbox
        # state into a concrete PerfettoConfig.
        return PerfettoConfig(
            duration_ms=duration_seconds * 1000,
            buffer_size_kb=buffer_size_kb,
            write_period_ms=self.settings_dialog.write_period.value(),
            flush_period_ms=self.settings_dialog.flush_period.value(),
            atrace_categories=categories,
            atrace_apps=atrace_apps,
            enable_ftrace=self.ds_ftrace.isChecked(),
            enable_process_stats=self.ds_process_stats.isChecked(),
            enable_sys_stats=self.ds_sys_stats.isChecked(),
            enable_system_info=self.ds_system_info.isChecked(),
            enable_surfaceflinger=self.ds_surfaceflinger.isChecked(),
            enable_gpu_memory=self.ds_gpu_memory.isChecked(),
            enable_packages_list=self.ds_packages_list.isChecked(),
            enable_android_log=self.ds_android_log.isChecked(),
        )

    def _build_request(self) -> PerfettoRequest:
        duration_seconds = self._duration_seconds()
        buffer_size_kb = self._buffer_kb()
        categories = self._selected_atrace_categories()
        atrace_apps = self._selected_atrace_apps()
        preset = None if self._current_preset == "custom" else self._current_preset
        config = None
        if preset is None:
            config = self._build_custom_config(
                duration_seconds,
                buffer_size_kb,
                categories,
                atrace_apps,
            )

        return PerfettoRequest(
            device_serial=self.device_serial or "",
            duration_seconds=duration_seconds,
            buffer_size_kb=buffer_size_kb,
            categories=categories,
            atrace_apps=atrace_apps,
            output_dir=self.output_path.output_dir(),
            preset=preset,
            config=config,
            auxiliary_options=self._auxiliary_options,
        )

    def _show_result_card(self) -> None:
        path = self.presenter.last_output_path
        if not path:
            return
        file_name = os.path.basename(path)
        try:
            size = os.path.getsize(path)
            file_size = f"{size / (1024 * 1024):.1f} MB" if size >= 1024 * 1024 else f"{size / 1024:.0f} KB"
        except OSError:
            file_size = ""
        self.result_card.show_result(
            file_name=file_name,
            file_size=file_size,
            duration=f"{self._duration_seconds()}s",
            show_perfetto_btn=True,
        )

    def start_capture(self) -> None:
        if not self.is_ready():
            return

        run_in_thread(
            self.presenter.run_request,
            self._build_request(),
        )
        self.capture_started.emit(self._duration_seconds())
