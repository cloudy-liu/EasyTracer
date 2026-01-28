from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class TraceviewPanel(QtWidgets.QWidget):
    def __init__(self, presenter: TraceviewPresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "10s", "30s", "Custom"])
        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)

        self.sample_radio = QtWidgets.QRadioButton("Sample Mode")
        self.trace_all_radio = QtWidgets.QRadioButton("Trace All")
        self.sample_radio.setChecked(True)
        self.sample_radio.toggled.connect(self._toggle_sampling)

        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setRange(1, 10000)
        self.interval_spin.setValue(1000)
        self.interval_spin.setSuffix(" ms")

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems(
            [
                "当前前台应用 (Top App)",
                "Launcher",
                "SystemUI",
                "Settings",
                "自定义包名",
            ]
        )
        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._toggle_target_input)

        self.cold_start_cb = QtWidgets.QCheckBox("冷启动模式 (force-stop)")

        self.output_path = OutputPathWidget(default_output_dir)

        self.start_button = QtWidgets.QPushButton("Start Trace")
        self.stop_button = QtWidgets.QPushButton("Stop Trace")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

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

        mode_row = QtWidgets.QHBoxLayout()
        mode_row.addWidget(self.sample_radio)
        mode_row.addWidget(self.trace_all_radio)

        target_row = QtWidgets.QHBoxLayout()
        target_row.addWidget(self.target_combo, 1)
        target_row.addWidget(self.target_input, 1)
        target_widget = QtWidgets.QWidget()
        target_widget.setLayout(target_row)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Duration:", duration_widget)
        form_layout.addRow("Mode:", mode_row)
        form_layout.addRow("Sampling Interval:", self.interval_spin)
        form_layout.addRow("Target:", target_widget)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Traceview Configuration"))
        layout.addLayout(form_layout)
        layout.addWidget(self.cold_start_cb)
        layout.addWidget(QtWidgets.QLabel("Output"))
        layout.addWidget(self.output_path)
        layout.addLayout(buttons)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        layout.addWidget(self.result_label)

        self.start_button.clicked.connect(self._on_start)
        self.stop_button.clicked.connect(self._on_stop)
        self.update_device(self.device_serial)

    def _toggle_custom_duration(self, text: str) -> None:
        self.custom_duration.setEnabled(text == "Custom")

    def _toggle_sampling(self) -> None:
        self.interval_spin.setEnabled(self.sample_radio.isChecked())

    def _toggle_target_input(self, text: str) -> None:
        self.target_input.setEnabled(text == "自定义包名")

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        self._update_buttons()
        if serial:
            self.status_label.setText(f"Selected device: {serial}")
        else:
            self.status_label.setText("Please select a device.")

    def update_view(self) -> None:
        busy = self.presenter.is_tracing
        self.progress.setVisible(busy)
        self._update_buttons()
        if busy:
            self.status_label.setText("Tracing in progress...")
        else:
            self.status_label.setText("Ready.")
        self.error_label.setText(
            f"Error: {self.presenter.error_message}" if self.presenter.error_message else ""
        )
        self.result_label.setText(
            f"Trace saved to: {self.presenter.last_output_path}" if self.presenter.last_output_path else ""
        )

    def _update_buttons(self) -> None:
        can_start = bool(self.device_serial) and not self.presenter.is_tracing
        can_stop = bool(self.device_serial) and self.presenter.is_tracing
        self.start_button.setEnabled(can_start)
        self.stop_button.setEnabled(can_stop)

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

    def _on_start(self) -> None:
        if not self.device_serial:
            return
        package = self._target_package() or ""
        run_in_thread(
            self.presenter.start_tracing,
            self.device_serial,
            package,
            self.sample_radio.isChecked(),
            int(self.interval_spin.value()),
        )

    def _on_stop(self) -> None:
        if not self.device_serial:
            return
        run_in_thread(
            self.presenter.stop_tracing,
            self.device_serial,
            self.output_path.output_dir(),
            self.output_path.create_subfolder(),
        )
