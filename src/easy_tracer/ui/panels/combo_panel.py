from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.combo_presenter import ComboPresenter
from easy_tracer.ui.qt_threading import run_in_thread


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class ComboPanel(QtWidgets.QWidget):
    def __init__(self, presenter: ComboPresenter, device_serial: Optional[str]):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self.perfetto_cb = QtWidgets.QCheckBox("Perfetto")
        self.simpleperf_cb = QtWidgets.QCheckBox("Simpleperf")
        self.systrace_cb = QtWidgets.QCheckBox("Systrace")
        self.traceview_cb = QtWidgets.QCheckBox("Traceview")
        self.perfetto_cb.setChecked(True)
        self.simpleperf_cb.setChecked(True)

        self.perfetto_mode = QtWidgets.QComboBox()
        self.perfetto_mode.addItems(["Normal", "Long"])
        self.simpleperf_freq = QtWidgets.QComboBox()
        self.simpleperf_freq.addItems(["500", "1000", "4000", "10000"])

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems(
            [
                "所有应用 (*)",
                "当前前台应用 (Top App)",
                "自定义包名",
            ]
        )
        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._toggle_target_input)

        self.cold_start_cb = QtWidgets.QCheckBox("冷启动模式 (force-stop)")
        self.duration_spin = QtWidgets.QSpinBox()
        self.duration_spin.setRange(1, 600)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" s")

        self.start_button = QtWidgets.QPushButton("开始组合抓取")
        self.start_button.setEnabled(False)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.status_label = QtWidgets.QLabel("Select a device to start.")
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setReadOnly(True)

        tools_layout = QtWidgets.QGridLayout()
        tools_layout.addWidget(self.perfetto_cb, 0, 0)
        tools_layout.addWidget(QtWidgets.QLabel("Mode:"), 0, 1)
        tools_layout.addWidget(self.perfetto_mode, 0, 2)
        tools_layout.addWidget(self.simpleperf_cb, 1, 0)
        tools_layout.addWidget(QtWidgets.QLabel("Freq:"), 1, 1)
        tools_layout.addWidget(self.simpleperf_freq, 1, 2)
        tools_layout.addWidget(self.systrace_cb, 2, 0)
        tools_layout.addWidget(self.traceview_cb, 2, 1)

        target_row = QtWidgets.QHBoxLayout()
        target_row.addWidget(self.target_combo, 1)
        target_row.addWidget(self.target_input, 1)

        config_form = QtWidgets.QFormLayout()
        config_form.addRow("Target:", target_row)
        config_form.addRow(self.cold_start_cb)
        config_form.addRow("Duration:", self.duration_spin)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("组合抓取配置"))
        layout.addLayout(tools_layout)
        layout.addLayout(config_form)
        layout.addWidget(self.start_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        layout.addWidget(QtWidgets.QLabel("Results"))
        layout.addWidget(self.result_text, 1)

        self.start_button.clicked.connect(self._on_start)
        self.update_device(self.device_serial)

    def _toggle_target_input(self, text: str) -> None:
        self.target_input.setEnabled(text == "自定义包名")

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        can_start = bool(serial) and not self.presenter.is_running
        self.start_button.setEnabled(can_start)
        if serial:
            self.status_label.setText(f"Selected device: {serial}")
        else:
            self.status_label.setText("Please select a device.")

    def update_view(self) -> None:
        busy = self.presenter.is_running
        self.progress.setVisible(busy)
        self.start_button.setEnabled(bool(self.device_serial) and not busy)
        if busy:
            self.status_label.setText("Combo capture running...")
        else:
            self.status_label.setText("Ready.")
        self.error_label.setText(self.presenter.error_message or "")
        if self.presenter.results:
            lines = [f"{k}: {v}" for k, v in self.presenter.results.items()]
            self.result_text.setPlainText("\n".join(lines))

    def _target_package(self) -> Optional[str]:
        text = self.target_combo.currentText()
        if text == "自定义包名":
            return self.target_input.text().strip() or None
        if text == "当前前台应用 (Top App)":
            return None
        return None

    def _on_start(self) -> None:
        if not self.device_serial:
            return

        enabled = {
            "systrace": self.systrace_cb.isChecked(),
            "perfetto": self.perfetto_cb.isChecked(),
            "simpleperf": self.simpleperf_cb.isChecked(),
            "traceview": self.traceview_cb.isChecked(),
        }

        configs = {
            "package_name": self._target_package(),
            "simpleperf_freq": int(self.simpleperf_freq.currentText()),
        }

        run_in_thread(
            self.presenter.start_combo,
            self.device_serial,
            int(self.duration_spin.value()),
            enabled,
            configs,
        )
