"""
Perfetto Panel
==============
Configuration and control panel for Perfetto trace recording.

Features:
- Preset-based configuration (Standard, Graphics, Memory, Full, Custom)
- Data source selection tabs
- Atrace category selection
- Auxiliary output options
"""

import os
from typing import Optional, Dict
from PySide6 import QtCore, QtWidgets, QtGui
from easy_tracer.framework.perfetto_config_builder import PerfettoConfig
from easy_tracer.models.requests import PerfettoRequest
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.components.cards import ResultCard
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog
from easy_tracer.ui.theme import Spacing


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
    ┌─ CAPTURE SETTINGS ────────────────────────────────────────┐
    │ Duration: [10s v]  Buffer: [150 MB v]                     │
    │ Output: [...output...]  [📂]  [Settings]                  │
    │ PRESETS: (Standard) (Graphics) (Memory) (Full) (Custom)   │
    └───────────────────────────────────────────────────────────┘
    ┌─ DATA SOURCES ────────────────────────────────────────────┐
    │ [CPU/Sched] [GPU/Graphics] [Memory] [Power] [Misc]        │
    └───────────────────────────────────────────────────────────┘
    ┌─ ATRACE CATEGORIES ───────────────────────────────────────┐
    │ Target Apps: [*                                         ] │
    │ [x] gfx [x] view [x] wm [x] am [x] sched ...              │
    └───────────────────────────────────────────────────────────┘
    """

    def __init__(self, presenter: PerfettoPresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._auxiliary_options: Dict[str, bool] = {}
        self._current_preset: str = "standard"
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

        # Row 1: Duration, Buffer, Mode
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

        self.open_output_btn = QtWidgets.QPushButton("📂")
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
        # ATRACE CATEGORIES GROUP
        # =====================================================================
        atrace_group = QtWidgets.QGroupBox("Atrace Categories")
        atrace_layout = QtWidgets.QVBoxLayout(atrace_group)
        atrace_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        atrace_layout.setSpacing(Spacing.SM)

        # Target apps
        app_row = QtWidgets.QHBoxLayout()
        app_row.addWidget(QtWidgets.QLabel("Target Apps:"))
        self.atrace_app = QtWidgets.QLineEdit()
        self.atrace_app.setPlaceholderText("* (all apps)")
        self.atrace_app.setText("*")
        app_row.addWidget(self.atrace_app, 1)
        atrace_layout.addLayout(app_row)

        # Category checkboxes
        self.atrace_checkboxes: Dict[str, QtWidgets.QCheckBox] = {}
        categories = [
            ("gfx", "Graphics"), ("input", "Input"), ("view", "View"),
            ("wm", "Window Manager"), ("am", "Activity Manager"), ("sched", "Scheduler"),
            ("freq", "CPU Freq"), ("idle", "CPU Idle"), ("dalvik", "Dalvik VM"),
            ("binder_driver", "Binder Driver"), ("binder_lock", "Binder Lock"),
            ("hal", "HAL"), ("res", "Resources"), ("webview", "WebView"),
            ("network", "Network"), ("audio", "Audio"), ("video", "Video"),
            ("camera", "Camera"),
        ]

        cat_grid = QtWidgets.QGridLayout()
        cat_grid.setSpacing(Spacing.SM)
        cols = 6
        for i, (cat_id, cat_label) in enumerate(categories):
            cb = QtWidgets.QCheckBox(cat_id)
            cb.setToolTip(cat_label)
            self.atrace_checkboxes[cat_id] = cb
            cat_grid.addWidget(cb, i // cols, i % cols)

        atrace_layout.addLayout(cat_grid)
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

    def _on_preset_toggled(self, checked: bool, preset_id: str) -> None:
        if checked:
            self._apply_preset(preset_id)

    def _apply_preset(self, preset_id: str) -> None:
        """Apply a preset configuration."""
        self._current_preset = preset_id

        # Preset configurations
        presets = {
            "standard": {
                "ds": {"ftrace": True, "process_stats": True, "sys_stats": False,
                       "system_info": False, "surfaceflinger": False, "gpu_memory": False,
                       "gpu_work": False, "heapprofd": False, "java_hprof": False,
                       "power": False, "perf": False, "packages_list": False,
                       "android_log": False, "network": False},
                "atrace": ["sched", "freq", "idle", "am", "wm", "gfx", "view",
                          "input", "dalvik", "binder_driver", "binder_lock"],
            },
            "graphics": {
                "ds": {"ftrace": True, "process_stats": True, "sys_stats": False,
                       "system_info": False, "surfaceflinger": True, "gpu_memory": True,
                       "gpu_work": False, "heapprofd": False, "java_hprof": False,
                       "power": False, "perf": False, "packages_list": False,
                       "android_log": False, "network": False},
                "atrace": ["sched", "freq", "idle", "am", "wm", "gfx", "view",
                          "input", "dalvik", "binder_driver", "binder_lock", "hal", "res"],
            },
            "memory": {
                "ds": {"ftrace": True, "process_stats": True, "sys_stats": True,
                       "system_info": False, "surfaceflinger": False, "gpu_memory": False,
                       "gpu_work": False, "heapprofd": False, "java_hprof": False,
                       "power": False, "perf": False, "packages_list": False,
                       "android_log": False, "network": False},
                "atrace": ["sched", "freq", "idle", "am", "wm", "gfx", "view", "dalvik"],
            },
            "full": {
                "ds": {"ftrace": True, "process_stats": True, "sys_stats": True,
                       "system_info": True, "surfaceflinger": True, "gpu_memory": True,
                       "gpu_work": False, "heapprofd": False, "java_hprof": False,
                       "power": False, "perf": False, "packages_list": True,
                       "android_log": True, "network": False},
                "atrace": ["sched", "freq", "idle", "am", "wm", "gfx", "view",
                          "input", "dalvik", "binder_driver", "binder_lock",
                          "hal", "res", "webview", "network", "audio", "video", "camera"],
            },
        }

        if preset_id == "custom":
            # Don't change anything, let user configure manually
            return

        config = presets.get(preset_id, presets["standard"])

        # Apply data sources
        ds = config["ds"]
        self.ds_ftrace.setChecked(ds["ftrace"])
        self.ds_process_stats.setChecked(ds["process_stats"])
        self.ds_sys_stats.setChecked(ds["sys_stats"])
        self.ds_system_info.setChecked(ds["system_info"])
        self.ds_surfaceflinger.setChecked(ds["surfaceflinger"])
        self.ds_gpu_memory.setChecked(ds["gpu_memory"])
        self.ds_gpu_work.setChecked(ds["gpu_work"])
        self.ds_heapprofd.setChecked(ds["heapprofd"])
        self.ds_java_hprof.setChecked(ds["java_hprof"])
        self.ds_power.setChecked(ds["power"])
        self.ds_perf.setChecked(ds["perf"])
        self.ds_packages_list.setChecked(ds["packages_list"])
        self.ds_android_log.setChecked(ds["android_log"])
        self.ds_network.setChecked(ds["network"])

        # Apply atrace categories
        atrace = config["atrace"]
        for cat_id, cb in self.atrace_checkboxes.items():
            cb.setChecked(cat_id in atrace)

    def set_auxiliary_options(self, options: Dict[str, bool]) -> None:
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

    def _selected_atrace_categories(self) -> list[str]:
        return [cat_id for cat_id, cb in self.atrace_checkboxes.items() if cb.isChecked()]

    def _duration_seconds(self) -> int:
        text = self.duration_combo.currentText()
        if text.endswith("min"):
            return int(text.replace("min", "")) * 60
        return int(text.replace("s", ""))

    def _buffer_kb(self) -> int:
        text = self.settings_dialog.buffer_combo.currentText().replace("MB", "").strip()
        return int(text) * 1024

    def _build_request(self) -> PerfettoRequest:
        preset = None if self._current_preset == "custom" else self._current_preset
        config = None

        if preset is None:
            config = PerfettoConfig(
                duration_ms=self._duration_seconds() * 1000,
                buffer_size_kb=self._buffer_kb(),
                write_period_ms=self.settings_dialog.write_period.value(),
                flush_period_ms=self.settings_dialog.flush_period.value(),
                atrace_categories=self._selected_atrace_categories(),
                enable_ftrace=self.ds_ftrace.isChecked(),
                enable_process_stats=self.ds_process_stats.isChecked(),
                enable_sys_stats=self.ds_sys_stats.isChecked(),
                enable_system_info=self.ds_system_info.isChecked(),
                enable_surfaceflinger=self.ds_surfaceflinger.isChecked(),
                enable_gpu_memory=self.ds_gpu_memory.isChecked(),
                enable_packages_list=self.ds_packages_list.isChecked(),
                enable_android_log=self.ds_android_log.isChecked(),
            )

        return PerfettoRequest(
            device_serial=self.device_serial or "",
            duration_seconds=self._duration_seconds(),
            buffer_size_kb=self._buffer_kb(),
            categories=self._selected_atrace_categories(),
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
        except Exception:
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
