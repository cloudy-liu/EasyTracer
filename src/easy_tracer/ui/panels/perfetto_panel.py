from typing import Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class PerfettoSettingsDialog(BaseSettingsDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, "Perfetto Settings")

        self.buffer_combo = QtWidgets.QComboBox()
        self.buffer_combo.addItems(["150 MB", "300 MB", "600 MB"])
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

        self.subfolder_cb = QtWidgets.QCheckBox("Create subfolder")
        self.subfolder_cb.setChecked(True)
        self.add_widget(self.subfolder_cb)


class PerfettoPanel(BasePanel):
    def __init__(self, presenter: PerfettoPresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        # --- Controls ---
        self.normal_radio = QtWidgets.QRadioButton("Normal")
        self.long_radio = QtWidgets.QRadioButton("Long")
        self.normal_radio.setChecked(True)
        self.normal_radio.toggled.connect(self._toggle_long_fields)

        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["10s", "30s", "60s", "10min"])

        # --- Settings Dialog ---
        self.settings_dialog = PerfettoSettingsDialog(self)
        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self.settings_dialog.exec)

        # --- Trace Categories ---
        self.atrace_list = QtWidgets.QListWidget()
        self.atrace_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._init_atrace_list()

        self.ftrace_list = QtWidgets.QListWidget()
        self.ftrace_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._init_ftrace_list()

        self.atrace_app = QtWidgets.QLineEdit()
        self.atrace_app.setPlaceholderText("Apps (*)")

        # --- Tabs ---
        self.data_tabs = QtWidgets.QTabWidget()
        self.data_tabs.addTab(self._build_core_tab(), "Core")
        self.data_tabs.addTab(self._build_gpu_tab(), "GPU")
        self.data_tabs.addTab(self._build_memory_tab(), "Memory")
        self.data_tabs.addTab(self._build_power_tab(), "Power")
        self.data_tabs.addTab(self._build_misc_tab(), "Misc")

        self.output_path = OutputPathWidget(
            default_output_dir,
            label="Output (Settings):",
            editable=False,
            tooltip="Shared output directory. Edit it in Settings panel.",
        )

        # --- Layout ---
        # Top Row: Duration | Normal/Long | Output | Settings
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(QtWidgets.QLabel("Duration:"))
        top_layout.addWidget(self.duration_combo)
        top_layout.addWidget(QtWidgets.QLabel("Mode:"))
        top_layout.addWidget(self.normal_radio)
        top_layout.addWidget(self.long_radio)
        top_layout.addWidget(self.output_path, 1) # Give output path stretch
        top_layout.addWidget(self.settings_btn)

        # Sources Area
        atrace_layout = QtWidgets.QVBoxLayout()
        atrace_layout.addWidget(QtWidgets.QLabel("Atrace Cats"))
        atrace_layout.addWidget(self.atrace_list)
        atrace_layout.addWidget(self.atrace_app)

        ftrace_layout = QtWidgets.QVBoxLayout()
        ftrace_layout.addWidget(QtWidgets.QLabel("Ftrace Events"))
        ftrace_layout.addWidget(self.ftrace_list)

        sources_layout = QtWidgets.QHBoxLayout()
        sources_layout.addLayout(atrace_layout, 1)
        sources_layout.addLayout(ftrace_layout, 1)

        # Main Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.data_tabs, 1)
        layout.addLayout(sources_layout, 1)

        self._toggle_long_fields()
        self.update_device(self.device_serial)

    def _init_atrace_list(self):
        cats = ["gfx", "input", "view", "wm", "am", "sched", "freq", "idle",
                "dalvik", "binder_driver", "binder_lock", "hal", "res", "webview", "network"]
        for cat in cats:
            item = QtWidgets.QListWidgetItem(cat)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked)
            self.atrace_list.addItem(item)

    def _init_ftrace_list(self):
        evts = ["sched/sched_switch", "sched/sched_wakeup", "power/cpu_frequency",
                "power/cpu_idle", "task/task_newtask", "task/task_rename"]
        for evt in evts:
            item = QtWidgets.QListWidgetItem(evt)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked)
            self.ftrace_list.addItem(item)

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
        self.settings_dialog.write_period.setEnabled(is_long)
        self.settings_dialog.flush_period.setEnabled(is_long)

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
            self.status_message.emit("Recording trace... Please wait.")
        else:
            self.status_message.emit("Ready.")

        if self.presenter.error_message:
            self.error_message.emit(self.presenter.error_message)
        elif self.presenter.last_output_path:
            self.status_message.emit(f"Trace saved to: {self.presenter.last_output_path}")

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
        text = self.settings_dialog.buffer_combo.currentText().replace("MB", "").strip()
        return int(text) * 1024

    def start_capture(self) -> None:
        if not self.is_ready():
            return

        run_in_thread(
            self.presenter.start_recording,
            self.device_serial,
            self._duration_seconds(),
            self._buffer_kb(),
            self._selected_atrace_categories(),
            self.output_path.output_dir(),
            self.settings_dialog.subfolder_cb.isChecked(),
        )
