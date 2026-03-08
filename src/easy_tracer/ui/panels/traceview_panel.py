from typing import Optional, Dict
from PySide6 import QtCore, QtWidgets, QtGui
from easy_tracer.models.requests import TraceviewStartRequest
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class TraceviewSettingsDialog(BaseSettingsDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, "Traceview Settings")

        self.sample_radio = QtWidgets.QRadioButton("Sample Mode")
        self.trace_all_radio = QtWidgets.QRadioButton("Trace All")
        self.sample_radio.setChecked(True)

        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(self.sample_radio)
        mode_layout.addWidget(self.trace_all_radio)
        mode_widget = QtWidgets.QWidget()
        mode_widget.setLayout(mode_layout)
        self.add_row("Mode:", mode_widget)

        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setRange(1, 10000)
        self.interval_spin.setValue(1000)
        self.interval_spin.setSuffix(" ms")
        self.add_row("Sampling Interval:", self.interval_spin)

        self.cold_start_cb = QtWidgets.QCheckBox("Cold Start (force-stop)")
        self.add_widget(self.cold_start_cb)

        self.sample_radio.toggled.connect(self._toggle_sampling)

    def _toggle_sampling(self) -> None:
        self.interval_spin.setEnabled(self.sample_radio.isChecked())


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

        # --- Controls ---
        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "10s", "30s", "Custom"])
        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems([
            "当前前台应用 (Top App)", "Launcher", "SystemUI", "Settings", "自定义包名"
        ])
        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._toggle_target_input)

        # --- Settings Dialog ---
        self.settings_dialog = TraceviewSettingsDialog(self)
        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self.settings_dialog.exec)

        self.output_path = OutputPathWidget(
            default_output_dir,
            label="",
            editable=False,
            tooltip="Shared output directory. Edit it in Settings panel.",
        )

        self.open_output_btn = QtWidgets.QPushButton("📂")
        self.open_output_btn.setToolTip("Open output directory")
        self.open_output_btn.setMaximumWidth(36)
        self.open_output_btn.clicked.connect(self._on_open_output)

        # --- Layout ---
        main_row = QtWidgets.QHBoxLayout()
        main_row.addWidget(QtWidgets.QLabel("Duration:"))
        main_row.addWidget(self.duration_combo)
        main_row.addWidget(self.custom_duration)
        main_row.addWidget(QtWidgets.QLabel("Target:"))
        main_row.addWidget(self.target_combo)
        main_row.addWidget(self.target_input, 1)
        main_row.addWidget(QtWidgets.QLabel("Output:"))
        main_row.addWidget(self.output_path, 1)
        main_row.addWidget(self.open_output_btn)
        main_row.addWidget(self.settings_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Traceview Configuration"))
        layout.addLayout(main_row)
        layout.addStretch(1)

        self.update_device(self.device_serial)

    def _toggle_custom_duration(self, text: str) -> None:
        self.custom_duration.setEnabled(text == "Custom")

    def _toggle_target_input(self, text: str) -> None:
        self.target_input.setEnabled(text == "自定义包名")

    def set_auxiliary_options(self, options: Dict[str, bool]) -> None:
        """Set auxiliary output options from main window."""
        self._auxiliary_options = options

    def _on_open_output(self) -> None:
        output_dir = self.output_path.output_dir()
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(output_dir))

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
        # For Traceview, we can always start if not busy
        self.readiness_changed.emit(self.is_ready() and not busy)

        if busy:
            self.status_message.emit("Tracing in progress...")
        else:
            self.status_message.emit("Ready.")

        if self.presenter.error_message:
            self.error_message.emit(self.presenter.error_message)
        elif self.presenter.last_output_path:
            self.status_message.emit(f"Trace saved to: {self.presenter.last_output_path}")

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
        if text == "自定义包名":
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
                sampling=self.settings_dialog.sample_radio.isChecked(),
                interval=self.settings_dialog.interval_spin.value(),
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
