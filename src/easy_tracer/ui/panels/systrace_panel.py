from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class SystracePanel(QtWidgets.QWidget):
    def __init__(self, presenter: SystracePresenter, device_serial: Optional[str], default_output_dir: str):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "7s", "10s", "30s", "Custom"])
        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)

        self.buffer_spin = QtWidgets.QSpinBox()
        self.buffer_spin.setRange(1024, 1024 * 1024)
        self.buffer_spin.setValue(10240)
        self.buffer_spin.setSuffix(" KB")

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems(
            [
                "所有应用 (*)",
                "当前前台应用 (Top App)",
                "Launcher",
                "SystemUI",
                "Settings",
                "自定义包名",
            ]
        )
        self.custom_target = QtWidgets.QLineEdit()
        self.custom_target.setPlaceholderText("com.example.app")
        self.custom_target.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._toggle_custom_target)

        self.atrace_filter = QtWidgets.QLineEdit()
        self.atrace_filter.setPlaceholderText("Filter categories...")
        self.atrace_filter.textChanged.connect(self._apply_atrace_filter)
        self.atrace_list = QtWidgets.QListWidget()
        self.atrace_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

        self.load_categories_button = QtWidgets.QPushButton("检测设备")
        self.load_categories_button.setEnabled(False)

        presets_layout = QtWidgets.QHBoxLayout()
        self.preset_min = QtWidgets.QPushButton("最小可用")
        self.preset_graphics = QtWidgets.QPushButton("图形分析")
        self.preset_system = QtWidgets.QPushButton("系统分析")
        self.preset_all = QtWidgets.QPushButton("全选")
        self.preset_clear = QtWidgets.QPushButton("清除")
        presets_layout.addWidget(self.preset_min)
        presets_layout.addWidget(self.preset_graphics)
        presets_layout.addWidget(self.preset_system)
        presets_layout.addWidget(self.preset_all)
        presets_layout.addWidget(self.preset_clear)

        self.ftrace_filter = QtWidgets.QLineEdit()
        self.ftrace_filter.setPlaceholderText("Filter ftrace events (gpu/kgsl)...")
        self.ftrace_filter.textChanged.connect(self._apply_ftrace_filter)
        self.ftrace_tree = QtWidgets.QTreeWidget()
        self.ftrace_tree.setHeaderLabels(["Ftrace Events"])

        self.load_ftrace_button = QtWidgets.QPushButton("检测设备")
        self.load_ftrace_button.setEnabled(False)

        self.tabs = QtWidgets.QTabWidget()
        atrace_tab = QtWidgets.QWidget()
        atrace_layout = QtWidgets.QVBoxLayout(atrace_tab)
        atrace_layout.addWidget(self.atrace_filter)
        atrace_layout.addLayout(presets_layout)
        atrace_layout.addWidget(self.load_categories_button, 0, QtCore.Qt.AlignRight)
        atrace_layout.addWidget(self.atrace_list, 1)

        ftrace_tab = QtWidgets.QWidget()
        ftrace_layout = QtWidgets.QVBoxLayout(ftrace_tab)
        ftrace_layout.addWidget(self.ftrace_filter)
        ftrace_layout.addWidget(self.load_ftrace_button, 0, QtCore.Qt.AlignRight)
        ftrace_layout.addWidget(self.ftrace_tree, 1)

        self.tabs.addTab(atrace_tab, "标准 Atrace")
        self.tabs.addTab(ftrace_tab, "设备 Ftrace")

        self.enhance_cb = QtWidgets.QCheckBox("Enhance Trace (增强线程名显示)")
        self.output_path = OutputPathWidget(default_output_dir)

        self.start_button = QtWidgets.QPushButton("Start Capture")
        self.start_button.setEnabled(False)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.status_label = QtWidgets.QLabel("")
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.result_label = QtWidgets.QLabel("")
        self.result_label.setStyleSheet("color: #1b5e20;")

        basic_form = QtWidgets.QFormLayout()
        duration_row = QtWidgets.QHBoxLayout()
        duration_row.addWidget(self.duration_combo)
        duration_row.addWidget(self.custom_duration)
        duration_container = QtWidgets.QWidget()
        duration_container.setLayout(duration_row)
        basic_form.addRow("Duration:", duration_container)
        basic_form.addRow("Buffer Size:", self.buffer_spin)

        target_row = QtWidgets.QHBoxLayout()
        target_row.addWidget(self.target_combo, 1)
        target_row.addWidget(self.custom_target, 1)
        target_container = QtWidgets.QWidget()
        target_container.setLayout(target_row)
        basic_form.addRow("Target:", target_container)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Systrace Configuration"))
        layout.addLayout(basic_form)
        layout.addWidget(QtWidgets.QLabel("Trace Categories"))
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.enhance_cb)
        layout.addWidget(QtWidgets.QLabel("Output"))
        layout.addWidget(self.output_path)
        layout.addWidget(self.start_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        layout.addWidget(self.result_label)

        self.load_categories_button.clicked.connect(self._on_load_categories)
        self.load_ftrace_button.clicked.connect(self._on_load_ftrace)
        self.start_button.clicked.connect(self._on_start_capture)
        self.preset_min.clicked.connect(lambda: self._apply_preset("min"))
        self.preset_graphics.clicked.connect(lambda: self._apply_preset("graphics"))
        self.preset_system.clicked.connect(lambda: self._apply_preset("system"))
        self.preset_all.clicked.connect(lambda: self._apply_preset("all"))
        self.preset_clear.clicked.connect(lambda: self._apply_preset("clear"))

        self.update_device(self.device_serial)

    def _toggle_custom_duration(self, text: str) -> None:
        self.custom_duration.setEnabled(text == "Custom")

    def _toggle_custom_target(self, text: str) -> None:
        self.custom_target.setEnabled(text == "自定义包名")

    def _apply_atrace_filter(self, text: str) -> None:
        needle = text.lower().strip()
        for i in range(self.atrace_list.count()):
            item = self.atrace_list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _apply_ftrace_filter(self, text: str) -> None:
        self._populate_ftrace_tree(self.presenter.ftrace_events, text)

    def _populate_ftrace_tree(self, events: list[str], filter_text: str = "") -> None:
        self.ftrace_tree.clear()
        needle = filter_text.lower().strip()
        grouped: dict[str, list[str]] = {}
        for event in events:
            if needle and needle not in event.lower():
                continue
            if "/" in event:
                group, name = event.split("/", 1)
            else:
                group, name = "misc", event
            grouped.setdefault(group, []).append(name)

        for group, names in sorted(grouped.items()):
            parent = QtWidgets.QTreeWidgetItem([group])
            for name in sorted(names):
                child = QtWidgets.QTreeWidgetItem([name])
                child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                child.setCheckState(0, QtCore.Qt.Unchecked)
                parent.addChild(child)
            self.ftrace_tree.addTopLevelItem(parent)
            parent.setExpanded(True)

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        can_load = bool(serial)
        self.load_categories_button.setEnabled(can_load)
        self.load_ftrace_button.setEnabled(can_load)
        self.start_button.setEnabled(can_load and bool(self.presenter.categories))
        if not serial:
            self.atrace_list.clear()
            self.ftrace_tree.clear()
            self.status_label.setText("Please select a device.")
        else:
            self.status_label.setText(f"Selected device: {serial}.")

    def update_view(self) -> None:
        busy = self.presenter.is_loading_categories or self.presenter.is_loading_ftrace or self.presenter.is_capturing
        self.progress.setVisible(busy)

        if self.presenter.categories and self.atrace_list.count() == 0:
            self.atrace_list.clear()
            defaults = {"sched", "freq", "idle", "am", "wm", "view", "gfx", "input", "dalvik", "binder_driver", "binder_lock"}
            for cat in self.presenter.categories:
                item = QtWidgets.QListWidgetItem(cat)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.Checked if cat in defaults else QtCore.Qt.Unchecked)
                self.atrace_list.addItem(item)

        if self.presenter.ftrace_events:
            self._populate_ftrace_tree(self.presenter.ftrace_events, self.ftrace_filter.text())

        self.error_label.setText(
            f"Error: {self.presenter.error_message}" if self.presenter.error_message else ""
        )
        self.result_label.setText(
            f"Capture saved to: {self.presenter.last_output_path}" if self.presenter.last_output_path else ""
        )

        if self.presenter.is_loading_categories:
            self.status_label.setText("Loading categories...")
        elif self.presenter.is_loading_ftrace:
            self.status_label.setText("Loading ftrace events...")
        elif self.presenter.is_capturing:
            self.status_label.setText("Capturing trace... Please wait.")
        else:
            self.status_label.setText("Ready.")

        can_run = bool(self.device_serial) and bool(self.presenter.categories) and not busy
        self.start_button.setEnabled(can_run)
        self.load_categories_button.setEnabled(bool(self.device_serial) and not busy)
        self.load_ftrace_button.setEnabled(bool(self.device_serial) and not busy)

    def _apply_preset(self, preset: str) -> None:
        if self.atrace_list.count() == 0:
            return
        presets = {
            "min": {"sched", "freq", "idle", "am", "wm", "view", "gfx", "input", "dalvik", "binder_driver", "binder_lock"},
            "graphics": {"sched", "freq", "idle", "am", "wm", "view", "gfx", "input", "dalvik", "binder_driver", "binder_lock", "webview", "res", "rs"},
            "system": {"sched", "freq", "idle", "am", "wm", "view", "gfx", "input", "dalvik", "binder_driver", "binder_lock", "hal", "ss", "pm", "power", "thermal", "disk", "sync", "memory", "memreclaim"},
        }
        for i in range(self.atrace_list.count()):
            item = self.atrace_list.item(i)
            if preset == "all":
                item.setCheckState(QtCore.Qt.Checked)
            elif preset == "clear":
                item.setCheckState(QtCore.Qt.Unchecked)
            else:
                item.setCheckState(QtCore.Qt.Checked if item.text() in presets[preset] else QtCore.Qt.Unchecked)

    def _on_load_categories(self) -> None:
        if not self.device_serial:
            return
        self.atrace_list.clear()
        run_in_thread(self.presenter.load_categories, self.device_serial)

    def _on_load_ftrace(self) -> None:
        if not self.device_serial:
            return
        self.ftrace_tree.clear()
        run_in_thread(self.presenter.load_ftrace_events, self.device_serial)

    def _get_duration(self) -> int:
        text = self.duration_combo.currentText()
        if text == "Custom":
            return int(self.custom_duration.value())
        return int(text.replace("s", ""))

    def _get_target_app(self) -> Optional[str]:
        text = self.target_combo.currentText()
        if text == "自定义包名":
            return self.custom_target.text().strip() or None
        if text == "Launcher":
            return "com.android.launcher3"
        if text == "SystemUI":
            return "com.android.systemui"
        if text == "Settings":
            return "com.android.settings"
        return None

    def _on_start_capture(self) -> None:
        if not self.device_serial:
            return
        selected = []
        for i in range(self.atrace_list.count()):
            item = self.atrace_list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(item.text())

        run_in_thread(
            self.presenter.start_capture,
            self.device_serial,
            selected,
            self._get_duration(),
            int(self.buffer_spin.value()),
            self._get_target_app(),
            self.output_path.output_dir(),
            self.output_path.create_subfolder(),
        )
