from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class PerfettoPanel(QtWidgets.QWidget):
    def __init__(self, presenter: PerfettoPresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self.normal_radio = QtWidgets.QRadioButton("Normal (内存缓冲)")
        self.long_radio = QtWidgets.QRadioButton("Long (实时写文件)")
        self.normal_radio.setChecked(True)

        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["10s", "30s", "60s", "10min"])
        self.buffer_combo = QtWidgets.QComboBox()
        self.buffer_combo.addItems(["150 MB", "300 MB", "600 MB"])

        self.write_period = QtWidgets.QSpinBox()
        self.write_period.setRange(500, 10000)
        self.write_period.setValue(2500)
        self.write_period.setSuffix(" ms")
        self.flush_period = QtWidgets.QSpinBox()
        self.flush_period.setRange(1000, 60000)
        self.flush_period.setValue(30000)
        self.flush_period.setSuffix(" ms")

        self.normal_radio.toggled.connect(self._toggle_long_fields)

        self.atrace_list = QtWidgets.QListWidget()
        self.atrace_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for cat in [
            "gfx",
            "input",
            "view",
            "wm",
            "am",
            "sched",
            "freq",
            "idle",
            "dalvik",
            "binder_driver",
            "binder_lock",
            "hal",
            "res",
            "webview",
            "network",
        ]:
            item = QtWidgets.QListWidgetItem(cat)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked)
            self.atrace_list.addItem(item)

        self.ftrace_list = QtWidgets.QListWidget()
        self.ftrace_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for evt in [
            "sched/sched_switch",
            "sched/sched_wakeup",
            "power/cpu_frequency",
            "power/cpu_idle",
            "task/task_newtask",
            "task/task_rename",
        ]:
            item = QtWidgets.QListWidgetItem(evt)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked)
            self.ftrace_list.addItem(item)

        self.atrace_app = QtWidgets.QLineEdit()
        self.atrace_app.setPlaceholderText("所有应用 (*)")

        self.data_tabs = QtWidgets.QTabWidget()
        self.data_tabs.addTab(self._build_core_tab(), "核心追踪")
        self.data_tabs.addTab(self._build_gpu_tab(), "渲染/GPU")
        self.data_tabs.addTab(self._build_memory_tab(), "内存分析")
        self.data_tabs.addTab(self._build_power_tab(), "电源/性能")
        self.data_tabs.addTab(self._build_misc_tab(), "日志/其他")

        self.output_path = OutputPathWidget(default_output_dir)

        self.start_button = QtWidgets.QPushButton("Start Recording")
        self.start_button.setEnabled(False)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.status_label = QtWidgets.QLabel("Select a device to start.")
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.result_label = QtWidgets.QLabel("")
        self.result_label.setStyleSheet("color: #1b5e20;")

        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(self.normal_radio)
        mode_layout.addWidget(self.long_radio)

        basic_form = QtWidgets.QFormLayout()
        basic_form.addRow("Duration:", self.duration_combo)
        basic_form.addRow("Buffer:", self.buffer_combo)
        basic_form.addRow("Write Period:", self.write_period)
        basic_form.addRow("Flush Period:", self.flush_period)

        atrace_layout = QtWidgets.QVBoxLayout()
        atrace_layout.addWidget(QtWidgets.QLabel("Atrace Categories"))
        atrace_layout.addWidget(self.atrace_list, 1)
        atrace_layout.addWidget(QtWidgets.QLabel("Atrace Apps"))
        atrace_layout.addWidget(self.atrace_app)

        ftrace_layout = QtWidgets.QVBoxLayout()
        ftrace_layout.addWidget(QtWidgets.QLabel("Ftrace Events"))
        ftrace_layout.addWidget(self.ftrace_list, 1)

        sources_layout = QtWidgets.QHBoxLayout()
        sources_layout.addLayout(atrace_layout, 1)
        sources_layout.addLayout(ftrace_layout, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Perfetto Configuration"))
        layout.addLayout(mode_layout)
        layout.addLayout(basic_form)
        layout.addWidget(self.data_tabs, 1)
        layout.addLayout(sources_layout, 1)
        layout.addWidget(QtWidgets.QLabel("Output"))
        layout.addWidget(self.output_path)
        layout.addWidget(self.start_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        layout.addWidget(self.result_label)

        self._toggle_long_fields()
        self.start_button.clicked.connect(self._on_start_recording)
        self.update_device(self.device_serial)

    def _build_core_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QCheckBox("linux.ftrace"))
        layout.addWidget(QtWidgets.QCheckBox("linux.process_stats"))
        layout.addWidget(QtWidgets.QCheckBox("linux.sys_stats"))
        layout.addWidget(QtWidgets.QCheckBox("linux.system_info"))
        layout.addStretch(1)
        return widget

    def _build_gpu_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QCheckBox("android.surfaceflinger.frametimeline"))
        layout.addWidget(QtWidgets.QCheckBox("android.surfaceflinger.frame"))
        layout.addWidget(QtWidgets.QCheckBox("android.gpu.memory"))
        layout.addWidget(QtWidgets.QCheckBox("android.gpu.work"))
        layout.addStretch(1)
        return widget

    def _build_memory_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QCheckBox("android.heapprofd"))
        layout.addWidget(QtWidgets.QCheckBox("android.java_hprof"))
        layout.addWidget(QtWidgets.QCheckBox("linux.kmem_activity"))
        layout.addStretch(1)
        return widget

    def _build_power_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QCheckBox("android.power"))
        layout.addWidget(QtWidgets.QCheckBox("linux.perf"))
        layout.addStretch(1)
        return widget

    def _build_misc_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QCheckBox("android.packages_list"))
        layout.addWidget(QtWidgets.QCheckBox("android.log"))
        layout.addWidget(QtWidgets.QCheckBox("android.network_packets"))
        layout.addWidget(QtWidgets.QCheckBox("track_event"))
        layout.addStretch(1)
        return widget

    def _toggle_long_fields(self) -> None:
        is_long = self.long_radio.isChecked()
        self.write_period.setEnabled(is_long)
        self.flush_period.setEnabled(is_long)

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        self.start_button.setEnabled(bool(serial))
        if serial:
            self.status_label.setText(f"Selected device: {serial}")
        else:
            self.status_label.setText("Please select a device.")

    def update_view(self) -> None:
        busy = self.presenter.is_recording
        self.progress.setVisible(busy)
        self.start_button.setEnabled(bool(self.device_serial) and not busy)
        if busy:
            self.status_label.setText("Recording trace... Please wait.")
        else:
            self.status_label.setText("Ready.")
        self.error_label.setText(
            f"Error: {self.presenter.error_message}" if self.presenter.error_message else ""
        )
        self.result_label.setText(
            f"Trace saved to: {self.presenter.last_output_path}" if self.presenter.last_output_path else ""
        )

    def _selected_atrace_categories(self) -> list[str]:
        selected = []
        for i in range(self.atrace_list.count()):
            item = self.atrace_list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(item.text())
        return selected

    def _duration_seconds(self) -> int:
        text = self.duration_combo.currentText()
        if text.endswith("min"):
            return int(text.replace("min", "")) * 60
        return int(text.replace("s", ""))

    def _buffer_kb(self) -> int:
        text = self.buffer_combo.currentText().replace("MB", "").strip()
        return int(text) * 1024

    def _on_start_recording(self) -> None:
        if not self.device_serial:
            return

        run_in_thread(
            self.presenter.start_recording,
            self.device_serial,
            self._duration_seconds(),
            self._buffer_kb(),
            self._selected_atrace_categories(),
            self.output_path.output_dir(),
            self.output_path.create_subfolder(),
        )
