"""
Traceview Panel
===============
Method-level tracing with inline mode selection.

Key settings (sample/trace-all mode, interval, cold-start) are surfaced
directly in the panel rather than hidden behind a settings dialog.
"""

from typing import Optional, Dict
from PySide6 import QtCore, QtWidgets, QtGui
from easy_tracer.models.requests import TraceviewStartRequest
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.theme import Spacing


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class TraceviewPanel(BasePanel):
    def __init__(self, presenter: TraceviewPresenter, device_serial: Optional[str], default_output_dir: str):
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
        self.duration_combo.addItems(["5s", "10s", "30s", "Custom"])
        row1.addWidget(self.duration_combo)

        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.custom_duration.setVisible(False)
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)
        row1.addWidget(self.custom_duration)

        row1.addWidget(QtWidgets.QLabel("Target:"))
        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems([
            "\u5f53\u524d\u524d\u53f0\u5e94\u7528 (Top App)", "Launcher", "SystemUI", "Settings", "\u81ea\u5b9a\u4e49\u5305\u540d"
        ])
        row1.addWidget(self.target_combo)

        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_input.setVisible(False)
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

        self.open_output_btn = QtWidgets.QPushButton()
        self.open_output_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        self.open_output_btn.setToolTip("Open output directory")
        self.open_output_btn.setMaximumWidth(36)
        self.open_output_btn.clicked.connect(self._on_open_output)
        row2.addWidget(self.open_output_btn)

        config_layout.addLayout(row2)
        layout.addWidget(config_group)

        # =====================================================================
        # TRACING MODE (inline — previously in modal dialog)
        # =====================================================================
        mode_group = QtWidgets.QGroupBox("Tracing Mode")
        mode_layout = QtWidgets.QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.MD)
        mode_layout.setSpacing(Spacing.XL)

        self.sample_radio = QtWidgets.QRadioButton("Sample Mode")
        self.trace_all_radio = QtWidgets.QRadioButton("Trace All Methods")
        self.sample_radio.setChecked(True)
        mode_layout.addWidget(self.sample_radio)
        mode_layout.addWidget(self.trace_all_radio)

        mode_layout.addWidget(QtWidgets.QLabel("Sampling Interval:"))
        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setRange(1, 10000)
        self.interval_spin.setValue(1000)
        self.interval_spin.setSuffix(" ms")
        mode_layout.addWidget(self.interval_spin)

        self.cold_start_cb = QtWidgets.QCheckBox("Cold Start")
        self.cold_start_cb.setToolTip("Force-stop app before tracing")
        mode_layout.addWidget(self.cold_start_cb)

        self.sample_radio.toggled.connect(self._toggle_sampling)

        mode_layout.addStretch()
        layout.addWidget(mode_group)

        layout.addStretch(1)

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _toggle_custom_duration(self, text: str) -> None:
        is_custom = text == "Custom"
        self.custom_duration.setEnabled(is_custom)
        self.custom_duration.setVisible(is_custom)

    def _toggle_target_input(self, text: str) -> None:
        is_custom = text == "\u81ea\u5b9a\u4e49\u5305\u540d"
        self.target_input.setEnabled(is_custom)
        self.target_input.setVisible(is_custom)

    def _toggle_sampling(self) -> None:
        self.interval_spin.setEnabled(self.sample_radio.isChecked())

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
        return bool(self.device_serial)

    def update_view(self) -> None:
        busy = self.presenter.is_tracing
        self.busy_changed.emit(busy)
        self.readiness_changed.emit(self.is_ready() and not busy)

        if busy:
            self.status_message.emit("Tracing in progress...")
        else:
            self.status_message.emit("Ready.")

        if self.presenter.error_message:
            self.error_message.emit(self.presenter.error_message)
        elif self.presenter.last_output_path:
            self.status_message.emit(f"Trace saved to: {self.presenter.last_output_path}")

    # =========================================================================
    # CAPTURE
    # =========================================================================

    def _duration_seconds(self) -> int:
        text = self.duration_combo.currentText()
        if text == "Custom":
            return int(self.custom_duration.value())
        return int(text.replace("s", ""))

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
        return None

    def start_capture(self) -> None:
        if not self.is_ready() or self.presenter.is_tracing:
            return
        package = self._target_package() or ""
        run_in_thread(
            self.presenter.start_request,
            TraceviewStartRequest(
                device_serial=self.device_serial or "",
                package_name=package,
                sampling=self.sample_radio.isChecked(),
                interval=self.interval_spin.value(),
                output_dir=self.output_path.output_dir(),
            ),
        )

    def stop_capture(self) -> None:
        if not self.device_serial or not self.presenter.is_tracing:
            return
        run_in_thread(
            self.presenter.stop_capture,
            self.output_path.output_dir(),
        )
