"""
Simpleperf Panel
================
CPU profiling with inline configuration options.

Key settings (frequency, cold-start, flamegraph, off-cpu) are surfaced
directly in the panel rather than hidden behind a settings dialog.
"""

from typing import Optional, Dict
from PySide6 import QtCore, QtWidgets, QtGui
from easy_tracer.models.requests import SimpleperfRequest
from easy_tracer.presenters.simpleperf_presenter import SimpleperfPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.components.cards import InfoCard
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.theme import Spacing


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class SimpleperfPanel(BasePanel):
    def __init__(self, presenter: SimpleperfPresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._auxiliary_options: Dict[str, bool] = {}
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
        # CAPTURE CONFIGURATION
        # =====================================================================
        config_group = QtWidgets.QGroupBox("Capture Configuration")
        config_layout = QtWidgets.QVBoxLayout(config_group)
        config_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        config_layout.setSpacing(Spacing.MD)

        # Row 1: Duration + Target
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(Spacing.LG)

        row1.addWidget(QtWidgets.QLabel("Duration:"))
        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "10s", "30s", "60s", "Custom"])
        row1.addWidget(self.duration_combo)

        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)
        row1.addWidget(self.custom_duration)

        row1.addWidget(QtWidgets.QLabel("Target:"))
        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems([
            "\u5f53\u524d\u524d\u53f0\u5e94\u7528 (Top App)", "Launcher", "SystemUI", "Settings",
            "system_server", "surfaceflinger", "\u7cfb\u7edf\u8303\u56f4 (System-wide)", "\u81ea\u5b9a\u4e49\u5305\u540d"
        ])
        row1.addWidget(self.target_combo)

        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._toggle_target_input)
        row1.addWidget(self.target_input, 1)

        config_layout.addLayout(row1)

        # Row 2: Output
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

        self.open_output_btn = QtWidgets.QPushButton("\U0001f4c2")
        self.open_output_btn.setToolTip("Open output directory")
        self.open_output_btn.setMaximumWidth(36)
        self.open_output_btn.clicked.connect(self._on_open_output)
        row2.addWidget(self.open_output_btn)

        config_layout.addLayout(row2)
        layout.addWidget(config_group)

        # =====================================================================
        # PROFILING OPTIONS (inline — previously in modal dialog)
        # =====================================================================
        options_group = QtWidgets.QGroupBox("Profiling Options")
        options_layout = QtWidgets.QHBoxLayout(options_group)
        options_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        options_layout.setSpacing(Spacing.XL)

        options_layout.addWidget(QtWidgets.QLabel("Frequency:"))
        self.freq_combo = QtWidgets.QComboBox()
        self.freq_combo.addItems(["500 Hz", "1000 Hz", "4000 Hz", "10000 Hz"])
        self.freq_combo.setCurrentIndex(2)
        options_layout.addWidget(self.freq_combo)

        self.cold_start_cb = QtWidgets.QCheckBox("Cold Start")
        self.cold_start_cb.setToolTip("Force-stop app before profiling")
        options_layout.addWidget(self.cold_start_cb)

        self.flamegraph_cb = QtWidgets.QCheckBox("Generate Flamegraph")
        self.flamegraph_cb.setChecked(True)
        options_layout.addWidget(self.flamegraph_cb)

        self.offcpu_cb = QtWidgets.QCheckBox("Trace Off-CPU")
        self.offcpu_cb.setChecked(True)
        options_layout.addWidget(self.offcpu_cb)

        options_layout.addStretch()
        layout.addWidget(options_group)

        # =====================================================================
        # INFO CARD
        # =====================================================================
        self.info_card = InfoCard(
            title="About Simpleperf",
            description=(
                "Simpleperf is a native CPU profiling tool for Android. "
                "It uses hardware performance counters to collect CPU samples "
                "with minimal overhead."
            ),
            bullets=[
                "App Profiling: Records call stacks of a specific app with configurable frequency",
                "System-wide: Profiles all processes (requires root or userdebug build)",
                "Cold Start: Force-stops the app first, then launches and profiles from startup",
                "Flamegraph: Generates an interactive HTML report for call stack visualization",
                "Off-CPU: Tracks time spent waiting (I/O, locks, sleep) in addition to on-CPU time",
            ],
        )
        layout.addWidget(self.info_card)

        layout.addStretch(1)

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _toggle_custom_duration(self, text: str) -> None:
        self.custom_duration.setEnabled(text == "Custom")

    def _toggle_target_input(self, text: str) -> None:
        self.target_input.setEnabled(text == "\u81ea\u5b9a\u4e49\u5305\u540d")

    def set_auxiliary_options(self, options: Dict[str, bool]) -> None:
        self._auxiliary_options = options

    def _on_open_output(self) -> None:
        output_dir = self.output_path.output_dir()
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(output_dir))

    # =========================================================================
    # DEVICE / VIEW
    # =========================================================================

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        self.readiness_changed.emit(self.is_ready())
        if serial:
            self.status_message.emit(f"Selected device: {serial}")
        else:
            self.status_message.emit("Please select a device.")

    def is_ready(self) -> bool:
        return bool(self.device_serial) and not self.presenter.is_profiling

    def update_view(self) -> None:
        busy = self.presenter.is_profiling
        self.busy_changed.emit(busy)
        self.readiness_changed.emit(self.is_ready())

        if busy:
            self.status_message.emit("Profiling... Please wait.")
        else:
            self.status_message.emit("Ready.")

        if self.presenter.error_message:
            self.error_message.emit(self.presenter.error_message)
        elif self.presenter.last_output_path:
            self.status_message.emit(f"Output saved to: {self.presenter.last_output_path}")

    # =========================================================================
    # CAPTURE
    # =========================================================================

    def _duration_seconds(self) -> int:
        text = self.duration_combo.currentText()
        if text == "Custom":
            return int(self.custom_duration.value())
        return int(text.replace("s", ""))

    def _frequency(self) -> int:
        text = self.freq_combo.currentText()
        return int(text.replace(" Hz", ""))

    def _target_package(self) -> Optional[str]:
        text = self.target_combo.currentText()
        mapping = {
            "Launcher": "com.android.launcher3",
            "SystemUI": "com.android.systemui",
            "Settings": "com.android.settings",
        }
        if text == "\u81ea\u5b9a\u4e49\u5305\u540d":
            return self.target_input.text().strip() or None
        if text in mapping:
            return mapping[text]
        if text in {"system_server", "surfaceflinger"}:
            return text
        return None

    def start_capture(self) -> None:
        if not self.is_ready():
            return

        target = self.target_combo.currentText()
        output_dir = self.output_path.output_dir()
        cold_start = self.cold_start_cb.isChecked()

        if target == "\u7cfb\u7edf\u8303\u56f4 (System-wide)":
            run_in_thread(
                self.presenter.run_request,
                SimpleperfRequest(
                    device_serial=self.device_serial or "",
                    duration_seconds=self._duration_seconds(),
                    frequency=self._frequency(),
                    output_dir=output_dir,
                    auxiliary_options=self._auxiliary_options,
                ),
            )
            return

        app_name = self._target_package()
        run_in_thread(
            self.presenter.run_request,
            SimpleperfRequest(
                device_serial=self.device_serial or "",
                app_name=app_name or "",
                duration_seconds=self._duration_seconds(),
                frequency=self._frequency(),
                output_dir=output_dir,
                cold_start=cold_start,
                auxiliary_options=self._auxiliary_options,
            ),
        )
