from typing import Optional
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog


DEFAULT_ATRACE_CATEGORIES = [
    "sched",
    "freq",
    "idle",
    "am",
    "wm",
    "view",
    "gfx",
    "input",
    "dalvik",
    "binder_driver",
    "binder_lock",
]
DEFAULT_ATRACE_SET = set(DEFAULT_ATRACE_CATEGORIES)


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class SystraceSettingsDialog(BaseSettingsDialog):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, "Systrace Settings")
        self.resize(520, 360)
        self.content_layout.setHorizontalSpacing(10)
        self.content_layout.setVerticalSpacing(10)

        self.buffer_spin = QtWidgets.QSpinBox()
        self.buffer_spin.setRange(1024, 1024 * 1024)
        self.buffer_spin.setValue(10240)
        self.buffer_spin.setSuffix(" KB")

        self.enhance_cb = QtWidgets.QCheckBox("增强线程名显示")

        self.subfolder_cb = QtWidgets.QCheckBox("Create subfolder")
        self.subfolder_cb.setChecked(True)

    def install_capture_widgets(
        self,
        duration_combo: QtWidgets.QComboBox,
        custom_duration: QtWidgets.QSpinBox,
        target_combo: QtWidgets.QComboBox,
        custom_target: QtWidgets.QLineEdit,
        output_path: OutputPathWidget,
    ) -> None:
        duration_row = QtWidgets.QWidget()
        duration_layout = QtWidgets.QHBoxLayout(duration_row)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(6)
        duration_layout.addWidget(duration_combo)
        duration_layout.addWidget(custom_duration)

        target_row = QtWidgets.QWidget()
        target_layout = QtWidgets.QHBoxLayout(target_row)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(6)
        target_layout.addWidget(target_combo)
        target_layout.addWidget(custom_target)

        capture_group = QtWidgets.QGroupBox("Capture")
        capture_layout = QtWidgets.QFormLayout(capture_group)
        capture_layout.setContentsMargins(8, 8, 8, 8)
        capture_layout.setHorizontalSpacing(8)
        capture_layout.setVerticalSpacing(8)
        capture_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
        capture_layout.addRow("Duration:", duration_row)
        capture_layout.addRow("Target:", target_row)

        output_group = QtWidgets.QGroupBox("Output")
        output_layout = QtWidgets.QVBoxLayout(output_group)
        output_layout.setContentsMargins(8, 8, 8, 8)
        output_layout.setSpacing(6)
        output_layout.addWidget(output_path)
        output_layout.addWidget(self.subfolder_cb)

        advanced_group = QtWidgets.QGroupBox("Advanced")
        advanced_layout = QtWidgets.QFormLayout(advanced_group)
        advanced_layout.setContentsMargins(8, 8, 8, 8)
        advanced_layout.setHorizontalSpacing(8)
        advanced_layout.setVerticalSpacing(8)
        advanced_layout.addRow("Buffer Size:", self.buffer_spin)
        advanced_layout.addRow(self.enhance_cb)

        self.add_widget(capture_group)
        self.add_widget(output_group)
        self.add_widget(advanced_group)


class SystracePanel(BasePanel):
    def __init__(
        self,
        presenter: SystracePresenter,
        device_serial: Optional[str],
        default_output_dir: str,
    ):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self.default_output_dir = default_output_dir
        self._auto_loaded_serial: Optional[str] = None
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self.settings_dialog = SystraceSettingsDialog(self)

        self.duration_combo = QtWidgets.QComboBox()
        self.duration_combo.addItems(["5s", "7s", "10s", "30s", "Custom"])
        self.custom_duration = QtWidgets.QSpinBox()
        self.custom_duration.setRange(1, 600)
        self.custom_duration.setValue(5)
        self.custom_duration.setSuffix(" s")
        self.custom_duration.setEnabled(False)
        self.duration_combo.currentTextChanged.connect(self._toggle_custom_duration)

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

        self.output_path = OutputPathWidget(
            default_output_dir,
            label="Output (Settings):",
            editable=False,
            tooltip="Shared output directory. Edit it in Settings panel.",
        )

        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self._open_settings)

        self.settings_dialog.install_capture_widgets(
            self.duration_combo,
            self.custom_duration,
            self.target_combo,
            self.custom_target,
            self.output_path,
        )

        self.settings_summary = QtWidgets.QLabel()
        self.settings_summary.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )
        # Styling is handled globally via app stylesheet.
        self._refresh_settings_summary()

        self.atrace_filter = QtWidgets.QLineEdit()
        self.atrace_filter.setPlaceholderText("Filter categories...")
        self.atrace_filter.textChanged.connect(self._apply_atrace_filter)
        self.atrace_list = QtWidgets.QListWidget()
        self.atrace_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.atrace_list.setViewMode(QtWidgets.QListView.IconMode)
        self.atrace_list.setFlow(QtWidgets.QListView.LeftToRight)
        self.atrace_list.setWrapping(True)
        self.atrace_list.setResizeMode(QtWidgets.QListView.Adjust)
        self.atrace_list.setMovement(QtWidgets.QListView.Static)
        self.atrace_list.setSpacing(2)
        self.atrace_list.setWordWrap(False)
        self.atrace_list.setUniformItemSizes(True)
        self.atrace_list.setGridSize(QtCore.QSize(120, 24))

        self.load_categories_button = QtWidgets.QPushButton("检测设备")
        self.load_categories_button.setEnabled(False)

        presets_layout = QtWidgets.QHBoxLayout()
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(4)
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
        atrace_layout.setContentsMargins(0, 0, 0, 0)
        atrace_layout.setSpacing(6)
        atrace_layout.addWidget(self.atrace_filter)
        atrace_layout.addLayout(presets_layout)
        atrace_layout.addWidget(self.load_categories_button, 0, QtCore.Qt.AlignRight)
        atrace_layout.addWidget(self.atrace_list, 1)

        ftrace_tab = QtWidgets.QWidget()
        ftrace_layout = QtWidgets.QVBoxLayout(ftrace_tab)
        ftrace_layout.setContentsMargins(0, 0, 0, 0)
        ftrace_layout.setSpacing(6)
        ftrace_layout.addWidget(self.ftrace_filter)
        ftrace_layout.addWidget(self.load_ftrace_button, 0, QtCore.Qt.AlignRight)
        ftrace_layout.addWidget(self.ftrace_tree, 1)

        self.tabs.addTab(atrace_tab, "标准 Atrace")
        self.tabs.addTab(ftrace_tab, "设备 Ftrace")

        # Refactored Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        top_controls_layout = QtWidgets.QHBoxLayout()
        top_controls_layout.addWidget(QtWidgets.QLabel("Capture:"))
        top_controls_layout.addWidget(self.settings_summary, 1)
        top_controls_layout.addWidget(self.settings_btn)

        layout.addLayout(top_controls_layout)
        layout.addWidget(self.tabs, 1)

        self.load_categories_button.clicked.connect(self._on_load_categories)
        self.load_ftrace_button.clicked.connect(self._on_load_ftrace)
        self.preset_min.clicked.connect(lambda: self._apply_preset("min"))
        self.preset_graphics.clicked.connect(lambda: self._apply_preset("graphics"))
        self.preset_system.clicked.connect(lambda: self._apply_preset("system"))
        self.preset_all.clicked.connect(lambda: self._apply_preset("all"))
        self.preset_clear.clicked.connect(lambda: self._apply_preset("clear"))

        self.update_device(self.device_serial)

    def _open_settings(self) -> None:
        self.settings_dialog.exec()
        self._refresh_settings_summary()

    def _compact_path(self, path: str, max_len: int = 48) -> str:
        path = (path or "").strip()
        if not path:
            return "-"
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len - 3) :]

    def _format_target_label(self) -> str:
        if self.custom_target.isEnabled():
            return self.custom_target.text().strip() or "Custom"
        return self.target_combo.currentText()

    def _refresh_settings_summary(self) -> None:
        duration = f"{self._get_duration()}s"
        target = self._format_target_label()
        output_dir = self._compact_path(self.output_path.output_dir())
        self.settings_summary.setText(
            f"Duration: {duration} | Target: {target} | Output: {output_dir}"
        )

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

        self._notify_readiness()

        if not serial:
            self.atrace_list.clear()
            self.ftrace_tree.clear()
            self._auto_loaded_serial = None
            self.status_message.emit("Please select a device.")
        else:
            self.status_message.emit(f"Selected device: {serial}.")
            should_auto_load = (
                serial != self._auto_loaded_serial
                or self.atrace_list.count() == 0
            )
            if should_auto_load:
                self._auto_loaded_serial = serial
                self._on_load_categories()

    def update_view(self) -> None:
        busy = (
            self.presenter.is_loading_categories
            or self.presenter.is_loading_ftrace
            or self.presenter.is_capturing
        )
        self.busy_changed.emit(busy)

        if self.presenter.categories and not self.presenter.is_loading_categories:
            if self.atrace_list.count() == 0:
                for cat in self.presenter.categories:
                    item = QtWidgets.QListWidgetItem(cat)
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                    item.setCheckState(
                        QtCore.Qt.Checked
                        if cat in DEFAULT_ATRACE_SET
                        else QtCore.Qt.Unchecked
                    )
                    self.atrace_list.addItem(item)

        if self.presenter.ftrace_events:
            self._populate_ftrace_tree(
                self.presenter.ftrace_events, self.ftrace_filter.text()
            )

        if self.presenter.error_message:
            self.error_message.emit(self.presenter.error_message)

        if self.presenter.last_output_path:
            self.status_message.emit(
                f"Capture saved to: {self.presenter.last_output_path}"
            )

        if self.presenter.is_loading_categories:
            self.status_message.emit("Loading categories...")
        elif self.presenter.is_loading_ftrace:
            self.status_message.emit("Loading ftrace events...")
        elif not self.presenter.is_capturing:
            self.status_message.emit("Ready.")

        self.load_categories_button.setEnabled(bool(self.device_serial) and not busy)
        self.load_ftrace_button.setEnabled(bool(self.device_serial) and not busy)
        self._notify_readiness()

    def _notify_readiness(self):
        busy = (
            self.presenter.is_loading_categories
            or self.presenter.is_loading_ftrace
            or self.presenter.is_capturing
        )
        can_run = bool(self.device_serial) and not busy
        self.readiness_changed.emit(can_run)

    def is_ready(self) -> bool:
        busy = (
            self.presenter.is_loading_categories
            or self.presenter.is_loading_ftrace
            or self.presenter.is_capturing
        )
        return bool(self.device_serial) and not busy

    def _apply_preset(self, preset: str) -> None:
        if self.atrace_list.count() == 0:
            return
        presets = {
            "min": {
                "sched",
                "freq",
                "idle",
                "am",
                "wm",
                "view",
                "gfx",
                "input",
                "dalvik",
                "binder_driver",
                "binder_lock",
            },
            "graphics": {
                "sched",
                "freq",
                "idle",
                "am",
                "wm",
                "view",
                "gfx",
                "input",
                "dalvik",
                "binder_driver",
                "binder_lock",
                "webview",
                "res",
                "rs",
            },
            "system": {
                "sched",
                "freq",
                "idle",
                "am",
                "wm",
                "view",
                "gfx",
                "input",
                "dalvik",
                "binder_driver",
                "binder_lock",
                "hal",
                "ss",
                "pm",
                "power",
                "thermal",
                "disk",
                "sync",
                "memory",
                "memreclaim",
            },
        }
        for i in range(self.atrace_list.count()):
            item = self.atrace_list.item(i)
            if preset == "all":
                item.setCheckState(QtCore.Qt.Checked)
            elif preset == "clear":
                item.setCheckState(QtCore.Qt.Unchecked)
            else:
                item.setCheckState(
                    QtCore.Qt.Checked
                    if item.text() in presets[preset]
                    else QtCore.Qt.Unchecked
                )

    def _on_load_categories(self) -> None:
        if not self.device_serial or self.presenter.is_loading_categories:
            return
        self.atrace_list.clear()
        run_in_thread(self.presenter.load_categories, self.device_serial)

    def _on_load_ftrace(self) -> None:
        if not self.device_serial or self.presenter.is_loading_ftrace:
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

    def start_capture(self) -> None:
        if not self.device_serial:
            self.error_message.emit("No device selected.")
            return
        selected = []
        for i in range(self.atrace_list.count()):
            item = self.atrace_list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(item.text())

        if not selected:
            if self.atrace_list.count() == 0:
                selected = list(DEFAULT_ATRACE_CATEGORIES)
                self.status_message.emit(
                    "Using default categories (device list unavailable)."
                )
            else:
                self.error_message.emit("No categories selected.")
                return

        buffer_size = self.settings_dialog.buffer_spin.value()
        create_subfolder = self.settings_dialog.subfolder_cb.isChecked()

        run_in_thread(
            self.presenter.start_capture,
            self.device_serial,
            selected,
            self._get_duration(),
            buffer_size,
            self._get_target_app(),
            self.output_path.output_dir(),
            create_subfolder,
        )

    def set_output_dir(self, output_dir: str) -> None:
        self.output_path.set_output_dir(output_dir)
        self._refresh_settings_summary()
