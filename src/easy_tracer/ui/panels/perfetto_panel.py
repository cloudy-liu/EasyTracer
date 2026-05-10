"""
Perfetto Panel
==============
Configuration and control panel for Perfetto trace recording.

Features:
- Direct data-source configuration with sensible defaults
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
)
from easy_tracer.models.requests import PerfettoRequest
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.components.cards import ResultCard
from easy_tracer.ui.components.perfetto_controls import (
    AtraceScopeEditor,
    DATA_SOURCE_SECTIONS,
    DEFAULT_SOURCE_PRESET,
    PerfettoDataSourceTabs,
    SOURCE_PRESET_ENABLED,
)
from easy_tracer.ui.dialogs.category_dialog import CategoryDialog
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
    +-- TRACE SETUP ------------------------------------------------+
    | Duration: [10s v]  Mode: (Normal) (Long)                      |
    | Output: [...output...]  [dir]  [Settings]                     |
    +---------------------------------------------------------------+
    +-- DATA SOURCES -----------------------------------------------+
    | [x] Ftrace        [x] Process Stats      [ ] SurfaceFlinger   |
    | [ ] GPU Memory    [ ] Sys Stats          [ ] System Info      |
    +---------------------------------------------------------------+
    +-- ATRACE SCOPE -----------------------------------------------+
    | Categories [Standard | 11/43] [Edit]                          |
    | Apps [All Apps (*) v] [com.example.app___________________]    |
    +---------------------------------------------------------------+
    """

    def __init__(
        self,
        presenter: PerfettoPresenter,
        device_serial: Optional[str],
        default_output_dir: str,
    ):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._auxiliary_options: dict[str, bool] = {}
        self._current_preset: str | None = None
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
        # TRACE SETUP GROUP
        # =====================================================================
        settings_group = QtWidgets.QGroupBox("Trace Setup")
        settings_layout = QtWidgets.QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(
            Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD
        )
        settings_layout.setSpacing(Spacing.SM)

        # Row 1: Duration, Mode
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(Spacing.LG)

        row1.addWidget(QtWidgets.QLabel("Duration:"))
        self.duration_combo = QtWidgets.QComboBox()
        self._configure_compact_combo(self.duration_combo, 6)
        self.duration_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
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

        self.open_output_btn = QtWidgets.QPushButton("Open")
        self.open_output_btn.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)
        )
        self.open_output_btn.setToolTip("Open output directory")
        self.open_output_btn.clicked.connect(self._on_open_output)
        row2.addWidget(self.open_output_btn)

        self.settings_dialog = PerfettoSettingsDialog(self)
        self.settings_btn = QtWidgets.QPushButton("Advanced")
        self.settings_btn.clicked.connect(self.settings_dialog.exec)
        row2.addWidget(self.settings_btn)

        settings_layout.addLayout(row2)

        layout.addWidget(settings_group)

        # =====================================================================
        # DATA SOURCES GROUP
        # =====================================================================
        sources_group = QtWidgets.QGroupBox("Data Sources")
        self.sources_group = sources_group
        sources_layout = QtWidgets.QVBoxLayout(sources_group)
        sources_layout.setContentsMargins(
            Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD
        )
        sources_layout.setSpacing(Spacing.SM)

        self.sources_status_label = None

        self.data_sources = PerfettoDataSourceTabs(DATA_SOURCE_SECTIONS)
        self.data_tabs = self.data_sources
        self._ds_map = self.data_sources.checkboxes
        for key, checkbox in self._ds_map.items():
            setattr(self, f"ds_{key}", checkbox)
        sources_layout.addWidget(self.data_tabs)

        layout.addWidget(sources_group)

        # =====================================================================
        # ATRACE GROUP (category summary + app scope)
        # =====================================================================
        atrace_group = QtWidgets.QGroupBox("Atrace Scope")
        self.atrace_group = atrace_group
        atrace_layout = QtWidgets.QVBoxLayout(atrace_group)
        atrace_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        atrace_layout.setSpacing(Spacing.SM)

        self.atrace_scope = AtraceScopeEditor(
            list(self._atrace_categories),
            len(CATEGORY_DESCRIPTIONS),
        )
        self.atrace_scope.category_edit_requested.connect(self._on_select_atrace)
        atrace_layout.addWidget(self.atrace_scope)

        self.atrace_header_row = self.atrace_scope.header_row
        self.atrace_app_widget = self.atrace_scope.app_widget
        self.atrace_target_combo = self.atrace_scope.target_combo
        self.atrace_custom_target = self.atrace_scope.custom_target
        self._category_summary = self.atrace_scope.category_summary

        layout.addWidget(atrace_group)

        # =====================================================================
        # RESULT CARD
        # =====================================================================
        self.result_card = ResultCard()
        self.result_card.open_output_clicked.connect(self._on_open_output)
        self.result_card.view_trace_clicked.connect(self._on_view_in_perfetto)
        layout.addWidget(self.result_card)

        self._apply_preset(DEFAULT_SOURCE_PRESET)

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

    # =========================================================================
    # PRESET APPLICATION
    # =========================================================================

    def _apply_preset(self, preset_id: str) -> None:
        """Apply default source/category combinations without exposing preset UI."""
        self._current_preset = preset_id

        enabled = SOURCE_PRESET_ENABLED.get(
            preset_id,
            SOURCE_PRESET_ENABLED["standard"],
        )
        self.data_sources.set_enabled_keys(enabled)

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
            self,
            all_cats,
            set(self.atrace_scope.selected_categories()),
        )
        if accepted:
            self._atrace_categories = selected
            self._update_category_summary()

    def _update_category_summary(self) -> None:
        self.atrace_scope.set_categories(
            self._atrace_categories,
            len(CATEGORY_DESCRIPTIONS),
        )

    def _selected_atrace_categories(self) -> list[str]:
        return self.atrace_scope.selected_categories()

    def _toggle_custom_target(self, text: str) -> None:
        self.atrace_scope.sync_custom_target(text)

    def _selected_atrace_apps(self) -> list[str]:
        return self.atrace_scope.selected_apps()

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
            self.status_message.emit(
                f"Trace saved to: {self.presenter.last_output_path}"
            )
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

    def _build_config(
        self,
        duration_seconds: int,
        buffer_size_kb: int,
        categories: list[str],
        atrace_apps: list[str],
    ) -> PerfettoConfig:
        """Build the explicit config from the visible checkbox state."""
        return PerfettoConfig(
            duration_ms=duration_seconds * 1000,
            buffer_size_kb=buffer_size_kb,
            write_period_ms=self.settings_dialog.write_period.value(),
            flush_period_ms=self.settings_dialog.flush_period.value(),
            atrace_categories=categories,
            atrace_apps=atrace_apps,
            enable_ftrace=self.data_sources.is_enabled("ftrace"),
            enable_process_stats=self.data_sources.is_enabled("process_stats"),
            enable_sys_stats=self.data_sources.is_enabled("sys_stats"),
            enable_system_info=self.data_sources.is_enabled("system_info"),
            enable_surfaceflinger=self.data_sources.is_enabled("surfaceflinger"),
            enable_gpu_memory=self.data_sources.is_enabled("gpu_memory"),
            enable_packages_list=self.data_sources.is_enabled("packages_list"),
            enable_android_log=self.data_sources.is_enabled("android_log"),
        )

    def _build_request(self) -> PerfettoRequest:
        duration_seconds = self._duration_seconds()
        buffer_size_kb = self._buffer_kb()
        categories = self._selected_atrace_categories()
        atrace_apps = self._selected_atrace_apps()
        config = self._build_config(
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
            preset=None,
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
            file_size = (
                f"{size / (1024 * 1024):.1f} MB"
                if size >= 1024 * 1024
                else f"{size / 1024:.0f} KB"
            )
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
