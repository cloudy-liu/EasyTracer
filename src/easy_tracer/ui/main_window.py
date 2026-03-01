from __future__ import annotations

import logging
from typing import Callable, List, Optional

from PySide6 import QtCore, QtWidgets
from easy_tracer.models.device import Device
from easy_tracer.presenters.main_presenter import MainPresenter
from easy_tracer.presenters.systrace_presenter import SystracePresenter
from easy_tracer.presenters.simpleperf_presenter import SimpleperfPresenter
from easy_tracer.presenters.perfetto_presenter import PerfettoPresenter
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.presenters.combo_presenter import ComboPresenter
from easy_tracer.services.config_service import ConfigService
from easy_tracer.ui.components.device_toolbar import DeviceToolbar
from easy_tracer.ui.components.log_panel import LogPanel
from easy_tracer.ui.theme import record_button_qss, Dimensions
from easy_tracer.ui import logging_bridge
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.panels.device_panel import DevicePanel
from easy_tracer.ui.panels.settings_panel import SettingsPanel
from easy_tracer.ui.panels.about_panel import AboutPanel
from easy_tracer.ui.qt_threading import Worker

logger = logging.getLogger(__name__)

PanelFactory = Callable[[], QtWidgets.QWidget]


class MainWindow(QtWidgets.QMainWindow):
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
        self.current_device: Optional[Device] = None
        self.systrace_presenter = systrace_presenter
        self.simpleperf_presenter = simpleperf_presenter
        self.perfetto_presenter = perfetto_presenter
        self.traceview_presenter = traceview_presenter
        self.combo_presenter = combo_presenter
        self._refresh_in_progress = False
        self._refresh_pending = False
        self._current_ready = False
        self._current_busy = False

        self.setWindowTitle("EasyTracer")
        self.resize(1100, 780)

        # Global record button: idle=record(green), busy=stop(red).
        self.record_button = QtWidgets.QPushButton("录制")
        self.record_button.setMinimumWidth(Dimensions.BUTTON_RECORD_WIDTH)
        self.record_button.clicked.connect(self._on_global_record_clicked)
        self.record_button.setEnabled(False)
        self._set_record_button_visuals(is_recording=False)

        # Toolbar
        self.toolbar = QtWidgets.QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.addToolBar(self.toolbar)

        self.device_toolbar = DeviceToolbar()
        self.device_toolbar.refresh_requested.connect(self.refresh_devices)
        self.device_toolbar.device_changed.connect(self._on_device_changed)
        self.device_toolbar.options_changed.connect(self._on_options_changed)
        self.toolbar.addWidget(self.device_toolbar)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.record_button)

        # Status Bar
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_progress = QtWidgets.QProgressBar()
        self.status_progress.setMaximumWidth(200)
        self.status_progress.setVisible(False)
        self.status_progress.setRange(0, 0)  # Indeterminate
        self.status_bar.addPermanentWidget(self.status_progress)

        self.nav_list = QtWidgets.QListWidget()
        self.nav_list.setMinimumWidth(150)
        self.nav_list.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Expanding,
        )
        nav_items = [
            ("Device", QtWidgets.QStyle.SP_ComputerIcon),
            ("Systrace", QtWidgets.QStyle.SP_FileDialogDetailedView),
            ("Perfetto", QtWidgets.QStyle.SP_ArrowRight),
            ("Simpleperf", QtWidgets.QStyle.SP_ArrowUp),
            ("Traceview", QtWidgets.QStyle.SP_FileDialogInfoView),
            ("Combo", QtWidgets.QStyle.SP_BrowserReload),
            ("Settings", QtWidgets.QStyle.SP_FileDialogContentsView),
            ("About", QtWidgets.QStyle.SP_MessageBoxInformation),
        ]
        for label, icon in nav_items:
            item = QtWidgets.QListWidgetItem(self.style().standardIcon(icon), label)
            self.nav_list.addItem(item)

        self.stack = QtWidgets.QStackedWidget()

        # Panels are created lazily to reduce cold-start time of the packaged EXE.
        # Indices MUST match nav_list rows:
        # 0 Device, 1 Systrace, 2 Perfetto, 3 Simpleperf, 4 Traceview, 5 Combo, 6 Settings, 7 About
        self.device_panel = DevicePanel()
        self.systrace_panel = None
        self.perfetto_panel = None
        self.simpleperf_panel = None
        self.traceview_panel = None
        self.combo_panel = None
        self.settings_panel = SettingsPanel(config_service)
        self.about_panel = AboutPanel()

        self._lazy_placeholders: dict[int, Optional[QtWidgets.QWidget]] = {}
        self._lazy_builders: dict[int, PanelFactory] = {
            1: self._build_systrace_panel,
            2: self._build_perfetto_panel,
            3: self._build_simpleperf_panel,
            4: self._build_traceview_panel,
            5: self._build_combo_panel,
        }

        self.stack.addWidget(self.device_panel)  # index 0
        for idx in range(1, 6):
            placeholder = QtWidgets.QWidget()
            self._lazy_placeholders[idx] = placeholder
            self.stack.addWidget(placeholder)
        self.stack.addWidget(self.settings_panel)  # index 6
        self.stack.addWidget(self.about_panel)  # index 7

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setCurrentRow(0)

        self.log_panel = LogPanel()
        self._qt_log_handler = logging_bridge.install_qt_logging(self.log_panel.append)
        self._qt_stdio_bridge = logging_bridge.install_qt_stdio(
            self.log_panel.append_stream
        )

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        body_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        body_splitter.addWidget(self.nav_list)
        body_splitter.addWidget(self.stack)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)

        log_widget = QtWidgets.QWidget()
        log_layout = QtWidgets.QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(QtWidgets.QLabel("Output Log"))
        log_layout.addWidget(self.log_panel, 1)

        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.main_splitter.addWidget(body_splitter)
        self.main_splitter.addWidget(log_widget)
        # Make the log area at least half by default (user can still drag to resize).
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setCollapsible(1, True)

        layout.addWidget(self.main_splitter, 1)

        self.setCentralWidget(central)

        # After first show/layout, apply a reasonable default splitter size.
        QtCore.QTimer.singleShot(0, self._init_splitter_sizes)

        # Apply settings at runtime (adb path, output dir) without restart.
        self.settings_panel.settings_saved.connect(self._apply_runtime_settings)

        if auto_refresh_devices:
            QtCore.QTimer.singleShot(0, self.refresh_devices)

    def _ensure_panel(self, index: int) -> QtWidgets.QWidget:
        """Ensure the panel widget for a given nav index exists.

        We keep QStackedWidget indices stable by swapping a lightweight placeholder
        with the real panel on first access.
        """
        builder = self._lazy_builders.get(index)
        if builder is None:
            return self.stack.widget(index)

        placeholder = self._lazy_placeholders.get(index)
        if placeholder is None:
            # Already swapped.
            return self.stack.widget(index)

        panel = builder()
        self.stack.removeWidget(placeholder)
        placeholder.deleteLater()
        self.stack.insertWidget(index, panel)
        self._lazy_placeholders[index] = None
        return panel

    def _current_device_serial(self) -> Optional[str]:
        return self.current_device.serial if self.current_device else None

    def _build_systrace_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.systrace_panel import SystracePanel

        panel = SystracePanel(
            self.systrace_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self.device_toolbar.output_options())
        self.systrace_panel = panel
        return panel

    def _build_perfetto_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.perfetto_panel import PerfettoPanel

        panel = PerfettoPanel(
            self.perfetto_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self.device_toolbar.output_options())
        self.perfetto_panel = panel
        return panel

    def _build_simpleperf_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.simpleperf_panel import SimpleperfPanel

        panel = SimpleperfPanel(
            self.simpleperf_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self.device_toolbar.output_options())
        self.simpleperf_panel = panel
        return panel

    def _build_traceview_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.traceview_panel import TraceviewPanel

        panel = TraceviewPanel(
            self.traceview_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self.device_toolbar.output_options())
        self.traceview_panel = panel
        return panel

    def _build_combo_panel(self) -> QtWidgets.QWidget:
        from easy_tracer.ui.panels.combo_panel import ComboPanel

        panel = ComboPanel(
            self.combo_presenter,
            self._current_device_serial(),
            self.config_service.output_dir,
        )
        panel.set_auxiliary_options(self.device_toolbar.output_options())
        self.combo_panel = panel
        return panel

    def warmup_ui(self) -> None:
        """Eagerly create all lazy panels.

        Intended for build-time warmup runs (to prime OS/AV caches) so that the
        first interactive launch feels snappy.
        """
        for idx in sorted(self._lazy_builders.keys()):
            self._ensure_panel(idx)

    def _log(self, message: str) -> None:
        self.log_panel.append(message)

    def _init_splitter_sizes(self) -> None:
        # Give more space to the log area (top: 300, bottom: remaining ~480)
        try:
            self.main_splitter.setSizes([500, 300])
        except Exception:
            pass

    def _on_nav_changed(self, index: int) -> None:
        if index < 0:
            return

        # Disconnect old panel signals if it was a BasePanel
        current = self.stack.currentWidget()
        if isinstance(current, BasePanel):
            try:
                current.readiness_changed.disconnect(self._update_start_button)
                current.busy_changed.disconnect(self._update_busy_state)
                current.status_message.disconnect(self.status_bar.showMessage)
                current.error_message.disconnect(self._show_error)
            except RuntimeError:
                pass  # Already disconnected or destroyed

        new_panel = self._ensure_panel(index)
        self.stack.setCurrentWidget(new_panel)

        # Default state
        self._current_ready = False
        self._current_busy = False
        self._update_record_button_state()
        self.status_bar.showMessage("Ready.")
        self.status_progress.setVisible(False)

        if isinstance(new_panel, BasePanel):
            new_panel.readiness_changed.connect(self._update_start_button)
            new_panel.busy_changed.connect(self._update_busy_state)
            new_panel.status_message.connect(self.status_bar.showMessage)
            new_panel.error_message.connect(self._show_error)

            # Initialize state from new panel
            self._update_start_button(new_panel.is_ready())
            # We assume panels aren't busy when switched to, or they update state immediately

        # Ensure device is propagated
        if hasattr(new_panel, "update_device"):
            serial = self.current_device.serial if self.current_device else None
            new_panel.update_device(serial)

    def _update_start_button(self, ready: bool) -> None:
        self._current_ready = ready
        self._update_record_button_state()

    def _update_busy_state(self, busy: bool) -> None:
        self._current_busy = busy
        self.status_progress.setVisible(busy)
        self._update_record_button_state()

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
        """Run in worker thread: single adb devices -l call."""
        return self.presenter.get_devices()

    def _on_refresh_finished(self) -> None:
        self._refresh_in_progress = False
        if self._refresh_pending:
            self._refresh_pending = False
            QtCore.QTimer.singleShot(0, self.refresh_devices)

    def _on_devices_loaded(self, devices: List[Device]) -> None:
        self.device_toolbar.set_devices(devices)
        self.device_panel.set_devices(devices)
        self._log(f"Found {len(devices)} device(s).")

    def _on_devices_error(self, message: str) -> None:
        self._log(f"Device refresh failed: {message}")

    def _on_device_changed(self, device: Optional[Device]) -> None:
        self.current_device = device
        self.presenter.on_device_selected(device)
        self.device_panel.set_selected_device(device)
        serial = device.serial if device else None

        # Propagate to all known panels once each.
        panels = []
        current = self.stack.currentWidget()
        if hasattr(current, "update_device"):
            panels.append(current)
        for panel in (
            self.systrace_panel,
            self.perfetto_panel,
            self.simpleperf_panel,
            self.traceview_panel,
            self.combo_panel,
        ):
            if panel is not None and hasattr(panel, "update_device"):
                panels.append(panel)

        seen: set[int] = set()
        for panel in panels:
            panel_id = id(panel)
            if panel_id in seen:
                continue
            seen.add(panel_id)
            panel.update_device(serial)

    def _on_options_changed(self) -> None:
        opts = self.device_toolbar.output_options()
        enabled = [name for name, flag in opts.items() if flag]
        self._log(f"附加输出选项: {', '.join(enabled) if enabled else 'None'}")

        # Propagate auxiliary options to all panels
        for panel in (
            self.systrace_panel,
            self.perfetto_panel,
            self.simpleperf_panel,
            self.traceview_panel,
            self.combo_panel,
        ):
            if panel is not None and hasattr(panel, "set_auxiliary_options"):
                panel.set_auxiliary_options(opts)

    def _apply_runtime_settings(self, adb_path: str, output_dir: str) -> None:
        # Update adb path - all adapters share the same AdbHelper instance via device_service.
        # Updating it once propagates to all.
        try:
            self.presenter.device_service.adb_adapter.adb_path = adb_path
        except Exception:
            logger.exception("Failed to update adb path")

        # Update output dir defaults in services.
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

        # Update UI output path widgets (defaults).
        if self.systrace_panel is not None:
            try:
                self.systrace_panel.set_output_dir(output_dir)
            except Exception:
                pass
        if self.perfetto_panel is not None:
            try:
                self.perfetto_panel.output_path.set_output_dir(output_dir)
            except Exception:
                pass
        if self.simpleperf_panel is not None:
            try:
                self.simpleperf_panel.output_path.set_output_dir(output_dir)
            except Exception:
                pass
        if self.traceview_panel is not None:
            try:
                self.traceview_panel.output_path.set_output_dir(output_dir)
            except Exception:
                pass

        # Combo uses sub-services, but keep its base dir consistent.
        try:
            self.combo_presenter.combo_service.output_dir = output_dir
        except Exception:
            pass

        self._log(f"Settings applied: adb={adb_path}, output={output_dir}")
        QtCore.QTimer.singleShot(0, self.refresh_devices)
