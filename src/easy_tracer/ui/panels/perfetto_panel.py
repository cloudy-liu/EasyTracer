"""
Perfetto Panel
==============
Configuration and control panel for Perfetto trace recording.

Features:
- Preset-based configuration (Standard, Graphics, Memory, Full, Custom)
- Data source selection tabs (Perfetto-specific)
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
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog
from easy_tracer.ui.theme import Spacing


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
    | [CPU/Sched] [GPU/Graphics] [Memory] [Power] [Misc]            |
    +---------------------------------------------------------------+
    +-- ATRACE -----------------------------------------------------+
    | Target Apps: [*                                            ]   |
    | Categories: Standard (11 of 45)                [Select...]    |
    | [am] [binder_driver] [binder_lock] [dalvik] [freq] [gfx] ... |
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
        sources_layout = QtWidgets.QVBoxLayout(sources_group)
        sources_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)

        self.data_tabs = QtWidgets.QTabWidget()
        self.data_tabs.addTab(self._build_core_tab(), "CPU/Sched")
        self.data_tabs.addTab(self._build_gpu_tab(), "GPU/Graphics")
        self.data_tabs.addTab(self._build_memory_tab(), "Memory")
        self.data_tabs.addTab(self._build_power_tab(), "Power")
        self.data_tabs.addTab(self._build_misc_tab(), "Misc")
        sources_layout.addWidget(self.data_tabs)

        layout.addWidget(sources_group)

        # =====================================================================
        # ATRACE GROUP (Target Apps + Category Summary)
        # =====================================================================
        atrace_group = QtWidgets.QGroupBox("Atrace")
        atrace_layout = QtWidgets.QVBoxLayout(atrace_group)
        atrace_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        atrace_layout.setSpacing(Spacing.SM)

        # Target apps row
        app_row = QtWidgets.QHBoxLayout()
        app_row.addWidget(QtWidgets.QLabel("Target Apps:"))
        self.atrace_app = QtWidgets.QLineEdit()
        self.atrace_app.setPlaceholderText("* (all apps)")
        self.atrace_app.setText("*")
        app_row.addWidget(self.atrace_app, 1)
        atrace_layout.addLayout(app_row)

        # Category summary with chip display
        self._category_summary = CategorySummaryWidget()
        self._category_summary.select_requested.connect(self._on_select_atrace)
        atrace_layout.addWidget(self._category_summary)

        layout.addWidget(atrace_group)

        # =====================================================================
        # RESULT CARD
        # =====================================================================
        self.result_card = ResultCard()
        self.result_card.open_output_clicked.connect(self._on_open_output)
        self.result_card.view_trace_clicked.connect(self._on_view_in_perfetto)
        layout.addWidget(self.result_card)

        # Build DS checkbox lookup after all tabs are created
        self._ds_map: dict[str, QtWidgets.QCheckBox] = {
            "ftrace": self.ds_ftrace,
            "process_stats": self.ds_process_stats,
            "sys_stats": self.ds_sys_stats,
            "system_info": self.ds_system_info,
            "surfaceflinger": self.ds_surfaceflinger,
            "gpu_memory": self.ds_gpu_memory,
            "gpu_work": self.ds_gpu_work,
            "heapprofd": self.ds_heapprofd,
            "java_hprof": self.ds_java_hprof,
            "power": self.ds_power,
            "perf": self.ds_perf,
            "packages_list": self.ds_packages_list,
            "android_log": self.ds_android_log,
            "network": self.ds_network,
        }

        # Connect preset buttons AFTER all UI is created
        for btn in self.preset_group.buttons():
            preset_id = btn.property("preset_id")
            btn.toggled.connect(lambda checked, p=preset_id: self._on_preset_toggled(checked, p))

        # Set default preset and apply it
        if self._standard_preset_btn:
            self._standard_preset_btn.setChecked(True)
        self._apply_preset("standard")

    # =========================================================================
    # DATA SOURCE TAB BUILDERS
    # =========================================================================

    def _build_core_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(Spacing.SM)

        self.ds_ftrace = QtWidgets.QCheckBox("linux.ftrace (CPU scheduling, system events)")
        self.ds_process_stats = QtWidgets.QCheckBox("linux.process_stats (Process memory, CPU)")
        self.ds_sys_stats = QtWidgets.QCheckBox("linux.sys_stats (System-wide memory info)")
        self.ds_system_info = QtWidgets.QCheckBox("linux.system_info (Kernel version, CPU info)")

        layout.addWidget(self.ds_ftrace)
        layout.addWidget(self.ds_process_stats)
        layout.addWidget(self.ds_sys_stats)
        layout.addWidget(self.ds_system_info)
        layout.addStretch(1)
        return widget

    def _build_gpu_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(Spacing.SM)

        self.ds_surfaceflinger = QtWidgets.QCheckBox("android.surfaceflinger.frametimeline (Frame timing)")
        self.ds_gpu_memory = QtWidgets.QCheckBox("android.gpu.memory (GPU memory usage)")
        self.ds_gpu_work = QtWidgets.QCheckBox("android.gpu.work (GPU workload)")

        layout.addWidget(self.ds_surfaceflinger)
        layout.addWidget(self.ds_gpu_memory)
        layout.addWidget(self.ds_gpu_work)
        layout.addStretch(1)
        return widget

    def _build_memory_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(Spacing.SM)

        self.ds_heapprofd = QtWidgets.QCheckBox("android.heapprofd (Native heap profiling)")
        self.ds_java_hprof = QtWidgets.QCheckBox("android.java_hprof (Java heap dump)")

        layout.addWidget(self.ds_heapprofd)
        layout.addWidget(self.ds_java_hprof)
        layout.addStretch(1)
        return widget

    def _build_power_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(Spacing.SM)

        self.ds_power = QtWidgets.QCheckBox("android.power (Power rail monitoring)")
        self.ds_perf = QtWidgets.QCheckBox("linux.perf (CPU performance counters)")

        layout.addWidget(self.ds_power)
        layout.addWidget(self.ds_perf)
        layout.addStretch(1)
        return widget

    def _build_misc_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(Spacing.SM)

        self.ds_packages_list = QtWidgets.QCheckBox("android.packages_list (Installed packages)")
        self.ds_android_log = QtWidgets.QCheckBox("android.log (Logcat integration)")
        self.ds_network = QtWidgets.QCheckBox("android.network_packets (Network traffic)")

        layout.addWidget(self.ds_packages_list)
        layout.addWidget(self.ds_android_log)
        layout.addWidget(self.ds_network)
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
        preset = None if self._current_preset == "custom" else self._current_preset
        config = None
        if preset is None:
            config = self._build_custom_config(
                duration_seconds,
                buffer_size_kb,
                categories,
            )

        return PerfettoRequest(
            device_serial=self.device_serial or "",
            duration_seconds=duration_seconds,
            buffer_size_kb=buffer_size_kb,
            categories=categories,
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
