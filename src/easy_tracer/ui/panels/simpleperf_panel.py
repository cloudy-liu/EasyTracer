from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.simpleperf_presenter import SimpleperfPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class SimpleperfPanel(QtWidgets.QWidget):
    def __init__(self, presenter: SimpleperfPresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "10s", "30s", "60s", "Custom"])
        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)

        self.freq_combo = QtWidgets.QComboBox()
        self.freq_combo.addItems(["500", "1000", "4000", "10000"])

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems(
            [
                "当前前台应用 (Top App)",
                "Launcher",
                "SystemUI",
                "Settings",
                "system_server",
                "surfaceflinger",
                "系统范围 (System-wide)",
                "自定义包名",
            ]
        )
        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._toggle_target_input)

        self.cold_start_cb = QtWidgets.QCheckBox("冷启动模式 (force-stop)")
        self.flamegraph_cb = QtWidgets.QCheckBox("生成火焰图")
        self.offcpu_cb = QtWidgets.QCheckBox("同时采集 Off-CPU 事件")
        self.flamegraph_cb.setChecked(True)
        self.offcpu_cb.setChecked(True)

        self.output_path = OutputPathWidget(default_output_dir)

        self.profile_button = QtWidgets.QPushButton("Start Capture")
        self.profile_button.setEnabled(False)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.status_label = QtWidgets.QLabel("Select a device to start.")
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.result_label = QtWidgets.QLabel("")
        self.result_label.setStyleSheet("color: #1b5e20;")

        duration_row = QtWidgets.QHBoxLayout()
        duration_row.addWidget(self.duration_combo)
        duration_row.addWidget(self.custom_duration)
        duration_widget = QtWidgets.QWidget()
        duration_widget.setLayout(duration_row)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Duration:", duration_widget)
        form_layout.addRow("Frequency:", self.freq_combo)

        target_row = QtWidgets.QHBoxLayout()
        target_row.addWidget(self.target_combo, 1)
        target_row.addWidget(self.target_input, 1)
        target_widget = QtWidgets.QWidget()
        target_widget.setLayout(target_row)
        form_layout.addRow("Target:", target_widget)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Simpleperf Configuration"))
        layout.addLayout(form_layout)
        layout.addWidget(self.cold_start_cb)
        layout.addWidget(self.flamegraph_cb)
        layout.addWidget(self.offcpu_cb)
        layout.addWidget(QtWidgets.QLabel("Output"))
        layout.addWidget(self.output_path)
        layout.addWidget(self.profile_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        layout.addWidget(self.result_label)

        self.profile_button.clicked.connect(self._on_profile)
        self.update_device(self.device_serial)

    def _toggle_custom_duration(self, text: str) -> None:
        self.custom_duration.setEnabled(text == "Custom")

    def _toggle_target_input(self, text: str) -> None:
        self.target_input.setEnabled(text == "自定义包名")

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        can_run = bool(serial) and not self.presenter.is_profiling
        self.profile_button.setEnabled(can_run)
        if serial:
            self.status_label.setText(f"Selected device: {serial}")
        else:
            self.status_label.setText("Please select a device.")

    def update_view(self) -> None:
        busy = self.presenter.is_profiling
        self.progress.setVisible(busy)
        self.profile_button.setEnabled(bool(self.device_serial) and not busy)
        if busy:
            self.status_label.setText("Profiling... Please wait.")
        else:
            self.status_label.setText("Ready.")
        self.error_label.setText(
            f"Error: {self.presenter.error_message}" if self.presenter.error_message else ""
        )
        self.result_label.setText(
            f"Output saved to: {self.presenter.last_output_path}" if self.presenter.last_output_path else ""
        )

    def _duration_seconds(self) -> int:
        text = self.duration_combo.currentText()
        if text == "Custom":
            return int(self.custom_duration.value())
        return int(text.replace("s", ""))

    def _frequency(self) -> int:
        return int(self.freq_combo.currentText())

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

    def _on_profile(self) -> None:
        if not self.device_serial:
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
