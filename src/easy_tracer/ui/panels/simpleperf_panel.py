from typing import Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.simpleperf_presenter import SimpleperfPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class SimpleperfSettingsDialog(BaseSettingsDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, "Simpleperf Settings")

        self.freq_combo = QtWidgets.QComboBox()
        self.freq_combo.addItems(["500", "1000", "4000", "10000"])
        self.add_row("Frequency:", self.freq_combo)

        self.cold_start_cb = QtWidgets.QCheckBox("Cold Start (force-stop)")
        self.add_widget(self.cold_start_cb)

        self.flamegraph_cb = QtWidgets.QCheckBox("Generate Flamegraph")
        self.flamegraph_cb.setChecked(True)
        self.add_widget(self.flamegraph_cb)

        self.offcpu_cb = QtWidgets.QCheckBox("Trace Off-CPU")
        self.offcpu_cb.setChecked(True)
        self.add_widget(self.offcpu_cb)


class SimpleperfPanel(BasePanel):
    def __init__(self, presenter: SimpleperfPresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        # --- Duration ---
        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "10s", "30s", "60s", "Custom"])
        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)

        # --- Target ---
        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems([
            "当前前台应用 (Top App)", "Launcher", "SystemUI", "Settings",
            "system_server", "surfaceflinger", "系统范围 (System-wide)", "自定义包名"
        ])
        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._toggle_target_input)

        # --- Settings Dialog ---
        self.settings_dialog = SimpleperfSettingsDialog(self)
        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self.settings_dialog.exec)

        self.output_path = OutputPathWidget(
            default_output_dir,
            label="Output (Settings):",
            editable=False,
            tooltip="Shared output directory. Edit it in Settings panel.",
        )

        # --- Layout ---
        main_row = QtWidgets.QHBoxLayout()
        main_row.addWidget(QtWidgets.QLabel("Duration:"))
        main_row.addWidget(self.duration_combo)
        main_row.addWidget(self.custom_duration)
        main_row.addWidget(QtWidgets.QLabel("Target:"))
        main_row.addWidget(self.target_combo)
        main_row.addWidget(self.target_input, 1)
        main_row.addWidget(self.output_path, 1)
        main_row.addWidget(self.settings_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Simpleperf Configuration"))
        layout.addLayout(main_row)
        layout.addStretch(1)

        self.update_device(self.device_serial)

    def _toggle_custom_duration(self, text: str) -> None:
        self.custom_duration.setEnabled(text == "Custom")

    def _toggle_target_input(self, text: str) -> None:
        self.target_input.setEnabled(text == "自定义包名")

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

    def _duration_seconds(self) -> int:
        text = self.duration_combo.currentText()
        if text == "Custom":
            return int(self.custom_duration.value())
        return int(text.replace("s", ""))

    def _frequency(self) -> int:
        return int(self.settings_dialog.freq_combo.currentText())

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
        if text in {"system_server", "surfaceflinger"}:
            return text
        return None

    def start_capture(self) -> None:
        if not self.is_ready():
            return

        target = self.target_combo.currentText()
        output_dir = self.output_path.output_dir()
        if target == "系统范围 (System-wide)":
            run_in_thread(
                self.presenter.start_system_profiling,
                self.device_serial,
                self._duration_seconds(),
                self._frequency(),
                output_dir,
            )
            return

        app_name = self._target_package()
        run_in_thread(
            self.presenter.start_app_profiling,
            self.device_serial,
            app_name or "",
            self._duration_seconds(),
            self._frequency(),
            output_dir,
        )
