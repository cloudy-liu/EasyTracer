from __future__ import annotations

import logging
from typing import Callable, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from easy_tracer.assets import load_icon
from easy_tracer.models.device import Device
from easy_tracer.presenters.combo_presenter import ComboPresenter
from easy_tracer.presenters.main_presenter import MainPresenter
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.presenters.simpleperf_presenter import SimpleperfPresenter
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.services.config_service import ConfigService
from easy_tracer.ui import logging_bridge
from easy_tracer.ui.components.log_panel import LogPanel
from easy_tracer.ui.panels.about_panel import AboutPanel
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.panels.device_panel import DevicePanel
from easy_tracer.ui.panels.settings_panel import SettingsPanel
from easy_tracer.ui.qt_threading import Worker
from easy_tracer.ui.theme import Colors, Dimensions, Typography, record_button_qss

logger = logging.getLogger(__name__)

PanelFactory = Callable[[], QtWidgets.QWidget]

BUSY_NAV_PREFIX = "\u25cf"

NAV_SECTIONS = [
    (
        "Tracers",
        [
            ("Systrace", "systrace", 1),
            ("Perfetto", "perfetto", 2),
            ("Simpleperf", "simpleperf", 3),
            ("Traceview", "traceview", 4),
            ("Combo", "combo", 5),
        ],
    ),
    (
        "System",
        [
            ("Device", "device", 0),
            ("Settings", "settings", 6),
            ("About", "about", 7),
        ],
    ),
]

PANEL_KEYS = {
    0: "device",
    1: "systrace",
    2: "perfetto",
    3: "simpleperf",
    4: "traceview",
    5: "combo",
    6: "settings",
    7: "about",
}


class MainWindow(QtWidgets.QMainWindow):
    """Primary application window for the EasyTracer desktop UI."""

    def __init__(
        self,
        presenter: MainPresenter,
        systrace_presenter: SystracePresenter,
        simpleperf_presenter: SimpleperfPresenter,
        perfetto_presenter: PerfettoPresenter,
        traceview_presenter: TraceviewPresenter,
        combo_presenter: ComboPresenter,
        config_service: ConfigService,
        auto_refresh_devices: bool = True,
    ):
        super().__init__()
        self.presenter = presenter
        self.config_service = config_service
        self.systrace_presenter = systrace_presenter
        self.simpleperf_presenter = simpleperf_presenter
        self.perfetto_presenter = perfetto_presenter
        self.traceview_presenter = traceview_presenter
        self.combo_presenter = combo_presenter

        self.current_device: Optional[Device] = None
        self._devices: List[Device] = []
        self._refresh_in_progress = False
        self._refresh_pending = False
        self._current_ready = False
        self._current_busy = False
        self._capture_duration = 0
        self._capture_elapsed = 0
        self._nav_buttons: dict[int, QtWidgets.QPushButton] = {}
        self._nav_base_text: dict[int, str] = {}

        self.setWindowTitle("EasyTracer")
        self.setWindowIcon(load_icon("app", size=64))
        self.resize(Dimensions.WINDOW_DEFAULT_WIDTH, Dimensions.WINDOW_DEFAULT_HEIGHT)

        self._countdown_timer = QtCore.QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        self._build_header_controls()
        self._build_stack()
        self._build_shell()
        self._build_status_bar()

        self._qt_log_handler = logging_bridge.install_qt_logging(self.log_panel.append)
        self._qt_stdio_bridge = logging_bridge.install_qt_stdio(self.log_panel.append_stream)

        self.settings_panel.settings_saved.connect(self._apply_runtime_settings)
        self._activate_stack_index(2)
        self._on_options_changed()

        if auto_refresh_devices:
            QtCore.QTimer.singleShot(0, self.refresh_devices)

    def _loaded_capture_panels(self) -> list[QtWidgets.QWidget]:
        """Returns all lazily built tracer panels that currently exist."""

        panels = [
            self.systrace_panel,
            self.perfetto_panel,
            self.simpleperf_panel,
            self.traceview_panel,
            self.combo_panel,
        ]
        return [panel for panel in panels if panel is not None]

    def _unique_panels(
        self,
        *panels: Optional[QtWidgets.QWidget],
    ) -> list[QtWidgets.QWidget]:
        """Returns panels without duplicates while preserving order."""

        unique_panels: list[QtWidgets.QWidget] = []
        seen: set[int] = set()
        for panel in panels:
            if panel is None:
                continue
            panel_id = id(panel)
            if panel_id in seen:
                continue
            seen.add(panel_id)
            unique_panels.append(panel)
        return unique_panels

    def _build_header_controls(self) -> None:
        self.record_button = QtWidgets.QPushButton("录制")
        self.record_button.setMinimumWidth(Dimensions.BUTTON_RECORD_WIDTH)
        self.record_button.clicked.connect(self._on_global_record_clicked)
        self.record_button.setEnabled(False)
        self._set_record_button_visuals(is_recording=False)

        self.device_label = QtWidgets.QLabel("Device:")
        self.device_label.setProperty("toolbarLabel", True)

        self.device_combo = QtWidgets.QComboBox()
        self.device_combo.setMinimumWidth(220)
        self.device_combo.setMaximumWidth(360)
        self.device_combo.currentIndexChanged.connect(self._on_device_selection_changed)

        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.refresh_button.clicked.connect(self.refresh_devices)

        self.toolbar_separator = QtWidgets.QFrame()
        self.toolbar_separator.setObjectName("toolbarSeparator")
        self.toolbar_separator.setFrameShape(QtWidgets.QFrame.VLine)
        self.toolbar_separator.setFixedSize(1, 28)

        self.aux_label = QtWidgets.QLabel("Capture extras")
        self.aux_label.setProperty("captionLabel", True)

        self.logcat_cb = QtWidgets.QCheckBox("Logcat")
        self.packages_cb = QtWidgets.QCheckBox("Packages")
        self.ps_cb = QtWidgets.QCheckBox("PS")
        self.meminfo_cb = QtWidgets.QCheckBox("Meminfo")
        self.logcat_cb.setChecked(True)
        self.packages_cb.setChecked(True)

        for checkbox in (self.logcat_cb, self.packages_cb, self.ps_cb, self.meminfo_cb):
            checkbox.stateChanged.connect(self._on_options_changed)

    def _build_stack(self) -> None:
        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("contentStack")

        self.device_panel = self._prepare_panel(DevicePanel(), 0)
        self.systrace_panel: Optional[QtWidgets.QWidget] = None
        self.perfetto_panel: Optional[QtWidgets.QWidget] = None
        self.simpleperf_panel: Optional[QtWidgets.QWidget] = None
        self.traceview_panel: Optional[QtWidgets.QWidget] = None
        self.combo_panel: Optional[QtWidgets.QWidget] = None
        self.settings_panel = self._prepare_panel(SettingsPanel(self.config_service), 6)
        self.about_panel = self._prepare_panel(AboutPanel(), 7)

        self._lazy_placeholders: dict[int, Optional[QtWidgets.QWidget]] = {}
        self._lazy_builders: dict[int, PanelFactory] = {
            1: self._build_systrace_panel,
            2: self._build_perfetto_panel,
            3: self._build_simpleperf_panel,
            4: self._build_traceview_panel,
            5: self._build_combo_panel,
        }

        self.stack.addWidget(self.device_panel)
        for index in range(1, 6):
            placeholder = QtWidgets.QWidget()
            placeholder.setProperty("panel_key", PANEL_KEYS[index])
            self._lazy_placeholders[index] = placeholder
            self.stack.addWidget(placeholder)
        self.stack.addWidget(self.settings_panel)
        self.stack.addWidget(self.about_panel)

    def _build_shell(self) -> None:
        central = QtWidgets.QWidget()
        central.setObjectName("prototypeShell")

        self.primary_toolbar_row = QtWidgets.QWidget()
        self.primary_toolbar_row.setObjectName("primaryToolbarRow")
        primary_layout = QtWidgets.QHBoxLayout(self.primary_toolbar_row)
        primary_layout.setContentsMargins(16, 8, 16, 8)
        primary_layout.setSpacing(12)
        primary_layout.addWidget(self.device_label)
        primary_layout.addWidget(self.device_combo)
        primary_layout.addWidget(self.refresh_button)
        primary_layout.addWidget(self.toolbar_separator)
        primary_layout.addWidget(self.record_button)
        primary_layout.addStretch(1)

        self.secondary_toolbar_row = QtWidgets.QWidget()
        self.secondary_toolbar_row.setObjectName("secondaryToolbarRow")
        secondary_layout = QtWidgets.QHBoxLayout(self.secondary_toolbar_row)
        secondary_layout.setContentsMargins(16, 4, 16, 8)
        secondary_layout.setSpacing(12)
        secondary_layout.addWidget(self.aux_label)
        secondary_layout.addWidget(self.logcat_cb)
        secondary_layout.addWidget(self.packages_cb)
        secondary_layout.addWidget(self.ps_cb)
        secondary_layout.addWidget(self.meminfo_cb)
        secondary_layout.addStretch(1)

        self.sidebar_nav = QtWidgets.QFrame()
        self.sidebar_nav.setObjectName("sidebarNav")
        self.sidebar_nav.setFixedWidth(160)
        sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar_nav)
        sidebar_layout.setContentsMargins(0, 8, 0, 8)
        sidebar_layout.setSpacing(0)
        for section_title, items in NAV_SECTIONS:
            self._add_nav_section(sidebar_layout, section_title, items)
        sidebar_layout.addStretch(1)

        self.content_stack_host = QtWidgets.QFrame()
        self.content_stack_host.setObjectName("contentStackHost")
        content_layout = QtWidgets.QVBoxLayout(self.content_stack_host)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.stack, 1)

        self.content_scroll = QtWidgets.QScrollArea()
        self.content_scroll.setObjectName("contentScrollArea")
        self.content_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setWidget(self.content_stack_host)

        self.main_column = QtWidgets.QWidget()
        self.main_column.setObjectName("mainColumn")
        main_column_layout = QtWidgets.QVBoxLayout(self.main_column)
        main_column_layout.setContentsMargins(0, 0, 0, 0)
        main_column_layout.setSpacing(0)

        self.log_panel = LogPanel()
        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.main_splitter.setObjectName("mainVerticalSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.addWidget(self.content_scroll)
        self.main_splitter.addWidget(self.log_panel)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([600, 100])
        main_column_layout.addWidget(self.main_splitter, 1)

        body = QtWidgets.QWidget()
        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self.sidebar_nav)
        body_layout.addWidget(self.main_column, 1)

        shell_layout = QtWidgets.QVBoxLayout(central)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        shell_layout.addWidget(self.primary_toolbar_row)
        shell_layout.addWidget(self.secondary_toolbar_row)
        shell_layout.addWidget(body, 1)

        central.setStyleSheet(self._shell_stylesheet())
        self.setCentralWidget(central)

    def _build_status_bar(self) -> None:
        self.status_bar = QtWidgets.QStatusBar()
        self.status_bar.setObjectName("statusBarContainer")
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

        self.status_progress = QtWidgets.QProgressBar()
        self.status_progress.setObjectName("statusProgress")
        self.status_progress.setMaximumWidth(220)
        self.status_progress.setVisible(False)
        self.status_progress.setRange(0, 0)
        self.status_progress.setTextVisible(True)
        self.status_bar.addPermanentWidget(self.status_progress)
        self.status_bar.showMessage("Ready.")

    def _shell_stylesheet(self) -> str:
        return f"""
        QWidget#prototypeShell {{
            background-color: {Colors.SURFACE};
            color: {Colors.NEUTRAL_900};
        }}

        QWidget#primaryToolbarRow {{
            background-color: {Colors.NEUTRAL_100};
            border-bottom: 1px solid {Colors.NEUTRAL_300};
        }}

        QWidget#secondaryToolbarRow {{
            background-color: {Colors.NEUTRAL_50};
            border-bottom: 1px solid {Colors.NEUTRAL_300};
        }}

        QFrame#toolbarSeparator {{
            background-color: {Colors.NEUTRAL_300};
        }}

        QLabel[toolbarLabel="true"] {{
            color: {Colors.NEUTRAL_700};
            font-size: {Typography.SIZE_BODY}px;
            font-weight: 600;
        }}

        QLabel[captionLabel="true"] {{
            color: {Colors.NEUTRAL_600};
            font-size: {Typography.SIZE_CAPTION}px;
        }}

        QFrame#sidebarNav {{
            background-color: {Colors.SURFACE};
            border-right: 1px solid {Colors.NEUTRAL_300};
        }}

        QLabel#navSectionTracers,
        QLabel#navSectionSystem {{
            color: {Colors.NEUTRAL_500};
            font-size: {Typography.SIZE_CAPTION}px;
            font-weight: 600;
            padding: 12px 16px 4px 16px;
        }}

        QPushButton[navButton="true"] {{
            border: none;
            border-left: 3px solid transparent;
            border-radius: 0;
            padding: 8px 16px;
            text-align: left;
            color: {Colors.NEUTRAL_800};
            background-color: transparent;
            font-size: {Typography.SIZE_BODY}px;
            font-weight: 500;
        }}

        QPushButton[navButton="true"]:hover {{
            background-color: {Colors.NEUTRAL_100};
        }}

        QPushButton[navButton="true"]:checked {{
            background-color: #e3f2fd;
            border-left: 3px solid {Colors.PRIMARY};
            color: {Colors.PRIMARY_DARK};
            font-weight: 600;
        }}

        QPushButton[navButton="true"][busy="true"] {{
            color: {Colors.SUCCESS};
        }}

        QFrame#contentStackHost {{
            background-color: {Colors.SURFACE};
        }}

        QScrollArea#contentScrollArea {{
            border: none;
            background-color: transparent;
        }}
        """

    def _add_nav_section(
        self,
        layout: QtWidgets.QVBoxLayout,
        title: str,
        items: list[tuple[str, str, int]],
    ) -> None:
        header = QtWidgets.QLabel(title.upper())
        header.setObjectName(f"navSection{title}")
        layout.addWidget(header)

        for label, icon_name, stack_index in items:
            button = QtWidgets.QPushButton(label)
            button.setProperty("navButton", True)
            button.setCheckable(True)
            button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            button.setIcon(load_icon(icon_name))
            button.setIconSize(QtCore.QSize(18, 18))
            button.clicked.connect(lambda checked=False, idx=stack_index: self._activate_stack_index(idx))
            self._nav_buttons[stack_index] = button
            self._nav_base_text[stack_index] = label
            layout.addWidget(button)

    def _prepare_panel(self, panel: QtWidgets.QWidget, index: int) -> QtWidgets.QWidget:
        key = PANEL_KEYS[index]
        panel.setProperty("panel_key", key)
        panel.setObjectName(f"panel_{key}")
        return panel

    def _ensure_panel(self, index: int) -> QtWidgets.QWidget:
        builder = self._lazy_builders.get(index)
        if builder is None:
            return self.stack.widget(index)

        placeholder = self._lazy_placeholders.get(index)
        if placeholder is None:
            return self.stack.widget(index)

        panel = self._prepare_panel(builder(), index)
        self.stack.removeWidget(placeholder)
        placeholder.deleteLater()
        self.stack.insertWidget(index, panel)
        self._lazy_placeholders[index] = None

        if isinstance(panel, BasePanel):
            panel.busy_changed.connect(
                lambda busy, stack_index=index: self._update_nav_badge(stack_index, busy)
            )
        return panel

    def _current_device_serial(self) -> Optional[str]:
        return self.current_device.serial if self.current_device else None

    def _selected_device(self) -> Optional[Device]:
        if not self._devices:
            return None
        data = self.device_combo.currentData()
        if isinstance(data, Device):
            return data
        index = self.device_combo.currentIndex()
        if index < 0 or index >= len(self._devices):
            return None
        return self._devices[index]

    def _output_options(self) -> dict[str, bool]:
        return {
            "logcat": self.logcat_cb.isChecked(),
            "packages": self.packages_cb.isChecked(),
            "ps": self.ps_cb.isChecked(),
            "meminfo": self.meminfo_cb.isChecked(),
        }

    def _build_systrace_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.systrace_panel import SystracePanel

        panel = SystracePanel(
            self.systrace_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self._output_options())
        self._bind_shared_output_dir(panel)
        self.systrace_panel = panel
        return panel

    def _build_perfetto_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.perfetto_panel import PerfettoPanel

        panel = PerfettoPanel(
            self.perfetto_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self._output_options())
        self._bind_shared_output_dir(panel)
        self.perfetto_panel = panel
        return panel

    def _build_simpleperf_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.simpleperf_panel import SimpleperfPanel

        panel = SimpleperfPanel(
            self.simpleperf_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self._output_options())
        self._bind_shared_output_dir(panel)
        self.simpleperf_panel = panel
        return panel

    def _build_traceview_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.traceview_panel import TraceviewPanel

        panel = TraceviewPanel(
            self.traceview_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self._output_options())
        self._bind_shared_output_dir(panel)
        self.traceview_panel = panel
        return panel

    def _build_combo_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.combo_panel import ComboPanel

        panel = ComboPanel(
            self.combo_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self._output_options())
        self._bind_shared_output_dir(panel)
        self.combo_panel = panel
        return panel

    def _bind_shared_output_dir(self, panel: QtWidgets.QWidget) -> None:
        output_path = getattr(panel, "output_path", None)
        if output_path is None or not hasattr(output_path, "output_dir_changed"):
            return
        output_path.output_dir_changed.connect(self._on_shared_output_dir_changed)

    def warmup_ui(self) -> None:
        """Eagerly creates all lazily loaded tracer panels."""

        for index in sorted(self._lazy_builders.keys()):
            self._ensure_panel(index)

    def _log(self, message: str) -> None:
        self.log_panel.append(message)

    def _activate_stack_index(self, index: int) -> None:
        current = self.stack.currentWidget()
        if isinstance(current, BasePanel):
            self._disconnect_panel_signals(current)

        new_panel = self._ensure_panel(index)
        self.stack.setCurrentWidget(new_panel)
        self._set_active_nav(index)

        self._current_ready = False
        self._current_busy = False
        self._capture_duration = 0
        self._capture_elapsed = 0
        self.status_progress.setVisible(False)
        self.status_bar.showMessage("Ready.")
        self._update_record_button_state()

        if isinstance(new_panel, BasePanel):
            self._connect_panel_signals(new_panel)
            self._update_start_button(new_panel.is_ready())

        if hasattr(new_panel, "update_device"):
            new_panel.update_device(self._current_device_serial())

    def _set_active_nav(self, active_index: int) -> None:
        for stack_index, button in self._nav_buttons.items():
            button.blockSignals(True)
            button.setChecked(stack_index == active_index)
            button.blockSignals(False)

    def _connect_panel_signals(self, panel: BasePanel) -> None:
        panel.readiness_changed.connect(self._update_start_button)
        panel.busy_changed.connect(self._update_busy_state)
        panel.status_message.connect(self.status_bar.showMessage)
        panel.error_message.connect(self._show_error)
        panel.capture_started.connect(self._on_capture_started)

    def _disconnect_panel_signals(self, panel: BasePanel) -> None:
        try:
            panel.readiness_changed.disconnect(self._update_start_button)
            panel.busy_changed.disconnect(self._update_busy_state)
            panel.status_message.disconnect(self.status_bar.showMessage)
            panel.error_message.disconnect(self._show_error)
            panel.capture_started.disconnect(self._on_capture_started)
        except (RuntimeError, TypeError):
            pass

    def _update_start_button(self, ready: bool) -> None:
        self._current_ready = ready
        self._update_record_button_state()

    def _update_busy_state(self, busy: bool) -> None:
        self._current_busy = busy
        if busy and self._capture_duration > 0:
            self.status_progress.setRange(0, self._capture_duration)
            self.status_progress.setValue(0)
            self.status_progress.setFormat(f"0s / {self._capture_duration}s")
            self.status_progress.setVisible(True)
            self._countdown_timer.start()
        elif busy:
            self.status_progress.setRange(0, 0)
            self.status_progress.setVisible(True)
        else:
            self._countdown_timer.stop()
            self._capture_duration = 0
            self._capture_elapsed = 0
            self.status_progress.setVisible(False)
        self._update_record_button_state()

    def _on_capture_started(self, duration: int) -> None:
        self._capture_duration = duration
        self._capture_elapsed = 0

    def _update_nav_badge(self, stack_index: int, busy: bool) -> None:
        button = self._nav_buttons.get(stack_index)
        if button is None:
            return
        button.setProperty("busy", busy)
        base_text = self._nav_base_text.get(stack_index, button.text())
        button.setText(f"{BUSY_NAV_PREFIX} {base_text}" if busy else base_text)
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    def _on_countdown_tick(self) -> None:
        self._capture_elapsed += 1
        if self._capture_elapsed <= self._capture_duration:
            self.status_progress.setValue(self._capture_elapsed)
            self.status_progress.setFormat(
                f"{self._capture_elapsed}s / {self._capture_duration}s"
            )
        self.status_bar.showMessage(
            f"Recording... {self._capture_elapsed}s / {self._capture_duration}s"
        )

    def _set_record_button_visuals(self, is_recording: bool) -> None:
        if is_recording:
            self.record_button.setText("停止")
            self.record_button.setIcon(
                self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop)
            )
        else:
            self.record_button.setText("录制")
            self.record_button.setIcon(
                self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
            )
        self.record_button.setStyleSheet(record_button_qss(is_recording))

    def _update_record_button_state(self) -> None:
        if self._current_busy:
            self.record_button.setEnabled(True)
            self._set_record_button_visuals(is_recording=True)
            return
        self.record_button.setEnabled(self._current_ready)
        self._set_record_button_visuals(is_recording=False)

    def _show_error(self, message: str) -> None:
        self.status_bar.showMessage(f"Error: {message}")
        self._log(f"Error: {message}")

    def _on_global_record_clicked(self) -> None:
        current = self.stack.currentWidget()
        if isinstance(current, BasePanel):
            if self._current_busy:
                current.stop_capture()
            else:
                current.start_capture()

    def refresh_devices(self) -> None:
        """Refreshes the connected Android device list in a worker thread."""

        if self._refresh_in_progress:
            self._refresh_pending = True
            return
        self._refresh_in_progress = True
        self._refresh_pending = False
        self._log("Refreshing devices...")
        worker = Worker(self._run_refresh_devices)
        worker.signals.result.connect(self._on_devices_loaded)
        worker.signals.error.connect(self._on_devices_error)
        worker.signals.finished.connect(self._on_refresh_finished)
        QtCore.QThreadPool.globalInstance().start(worker)

    def _run_refresh_devices(self) -> List[Device]:
        """Runs the device query in a background worker."""

        return self.presenter.get_devices()

    def _on_refresh_finished(self) -> None:
        self._refresh_in_progress = False
        if self._refresh_pending:
            self._refresh_pending = False
            QtCore.QTimer.singleShot(0, self.refresh_devices)

    def _on_devices_loaded(self, devices: List[Device]) -> None:
        self._devices = devices
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        if not devices:
            self.device_combo.addItem("No devices")
        else:
            for device in devices:
                self.device_combo.addItem(str(device), device)
        self.device_combo.blockSignals(False)
        self._on_device_selection_changed(self.device_combo.currentIndex())
        self.device_panel.set_devices(devices)
        self._log(f"Found {len(devices)} device(s).")

    def _on_devices_error(self, message: str) -> None:
        self._log(f"Device refresh failed: {message}")

    def _on_device_selection_changed(self, _index: int) -> None:
        self._on_device_changed(self._selected_device())

    def _on_device_changed(self, device: Optional[Device]) -> None:
        self.current_device = device
        self.presenter.on_device_selected(device)
        self.device_panel.set_selected_device(device)
        serial = self._current_device_serial()

        current = self.stack.currentWidget()
        for panel in self._unique_panels(current, *self._loaded_capture_panels()):
            if hasattr(panel, "update_device"):
                panel.update_device(serial)

    def _on_options_changed(self) -> None:
        options = self._output_options()
        enabled = [name for name, flag in options.items() if flag]
        self._log(
            f"Capture extras: {', '.join(enabled) if enabled else 'none'}"
        )
        for panel in self._loaded_capture_panels():
            if hasattr(panel, "set_auxiliary_options"):
                panel.set_auxiliary_options(options)

    def _apply_adb_path(self, adb_path: str) -> None:
        try:
            self.presenter.device_service.adb_adapter.adb_path = adb_path
        except Exception:
            logger.exception("Failed to update adb path")

    def _set_panel_output_dir(self, panel: Optional[QtWidgets.QWidget], output_dir: str) -> None:
        if panel is None:
            return
        setter = getattr(panel, "set_output_dir", None)
        if callable(setter):
            try:
                setter(output_dir)
                return
            except Exception:
                pass

        output_path = getattr(panel, "output_path", None)
        if output_path is None:
            return
        try:
            output_path.set_output_dir(output_dir)
        except Exception:
            pass

    def _apply_output_dir(self, output_dir: str) -> None:
        try:
            self.systrace_presenter.capture_service.output_dir = output_dir
        except Exception:
            logger.exception("Failed to update output_dir for systrace")

        try:
            self.perfetto_presenter.perfetto_service.output_dir = output_dir
        except Exception:
            logger.exception("Failed to update output_dir for perfetto")

        try:
            self.simpleperf_presenter.simpleperf_service.output_dir = output_dir
        except Exception:
            logger.exception("Failed to update output_dir for simpleperf")

        try:
            self.traceview_presenter.traceview_service.output_dir = output_dir
        except Exception:
            logger.exception("Failed to update output_dir for traceview")

        self._set_panel_output_dir(self.systrace_panel, output_dir)
        self._set_panel_output_dir(self.perfetto_panel, output_dir)
        self._set_panel_output_dir(self.simpleperf_panel, output_dir)
        self._set_panel_output_dir(self.traceview_panel, output_dir)
        self._set_panel_output_dir(self.combo_panel, output_dir)

        try:
            self.combo_presenter.combo_service.output_dir = output_dir
        except Exception:
            pass

        try:
            self.settings_panel.output_input.setText(output_dir)
        except Exception:
            pass

    def _on_shared_output_dir_changed(self, output_dir: str) -> None:
        output_dir = (output_dir or "").strip()
        if not output_dir:
            return
        self.config_service.update(
            adb_path=self.config_service.adb_path,
            output_dir=output_dir,
        )
        self._apply_output_dir(self.config_service.output_dir)
        self._log(f"Output directory updated: {self.config_service.output_dir}")

    def _apply_runtime_settings(self, adb_path: str, output_dir: str) -> None:
        self._apply_adb_path(adb_path)
        self._apply_output_dir(output_dir)
        self._log(f"Settings applied: adb={adb_path}, output={output_dir}")
        QtCore.QTimer.singleShot(0, self.refresh_devices)
