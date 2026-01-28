from __future__ import annotations

from typing import List, Optional
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
from easy_tracer.ui.panels.device_panel import DevicePanel
from easy_tracer.ui.panels.systrace_panel import SystracePanel
from easy_tracer.ui.panels.perfetto_panel import PerfettoPanel
from easy_tracer.ui.panels.simpleperf_panel import SimpleperfPanel
from easy_tracer.ui.panels.traceview_panel import TraceviewPanel
from easy_tracer.ui.panels.combo_panel import ComboPanel
from easy_tracer.ui.panels.settings_panel import SettingsPanel
from easy_tracer.ui.panels.about_panel import AboutPanel
from easy_tracer.ui.qt_threading import Worker


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
    ):
        super().__init__()
        self.presenter = presenter
        self.config_service = config_service
        self.current_device: Optional[Device] = None
        self._refresh_in_progress = False
        self._refresh_pending = False

        self.setWindowTitle("EasyTracer")
        self.resize(1100, 780)

        self.device_toolbar = DeviceToolbar()
        self.device_toolbar.refresh_requested.connect(self.refresh_devices)
        self.device_toolbar.device_changed.connect(self._on_device_changed)
        self.device_toolbar.options_changed.connect(self._on_options_changed)

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
        self.device_panel = DevicePanel()
        self.systrace_panel = SystracePanel(
            systrace_presenter, None, config_service.output_dir
        )
        self.perfetto_panel = PerfettoPanel(
            perfetto_presenter, None, config_service.output_dir
        )
        self.simpleperf_panel = SimpleperfPanel(
            simpleperf_presenter, None, config_service.output_dir
        )
        self.traceview_panel = TraceviewPanel(
            traceview_presenter, None, config_service.output_dir
        )
        self.combo_panel = ComboPanel(combo_presenter, None)
        self.settings_panel = SettingsPanel(config_service)
        self.about_panel = AboutPanel()

        self.stack.addWidget(self.device_panel)
        self.stack.addWidget(self.systrace_panel)
        self.stack.addWidget(self.perfetto_panel)
        self.stack.addWidget(self.simpleperf_panel)
        self.stack.addWidget(self.traceview_panel)
        self.stack.addWidget(self.combo_panel)
        self.stack.addWidget(self.settings_panel)
        self.stack.addWidget(self.about_panel)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

        self.log_panel = LogPanel()

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.device_toolbar)

        body_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        body_splitter.addWidget(self.nav_list)
        body_splitter.addWidget(self.stack)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        top_layout.addWidget(body_splitter, 1)

        log_widget = QtWidgets.QWidget()
        log_layout = QtWidgets.QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(QtWidgets.QLabel("Output Log"))
        log_layout.addWidget(self.log_panel, 1)

        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(log_widget)
        main_splitter.setStretchFactor(0, 4)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setCollapsible(1, True)

        layout.addWidget(main_splitter, 1)

        self.setCentralWidget(central)

        QtCore.QTimer.singleShot(0, self.refresh_devices)

    def _log(self, message: str) -> None:
        self.log_panel.append(message)

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
        self.systrace_panel.update_device(serial)
        self.perfetto_panel.update_device(serial)
        self.simpleperf_panel.update_device(serial)
        self.traceview_panel.update_device(serial)
        self.combo_panel.update_device(serial)

    def _on_options_changed(self) -> None:
        opts = self.device_toolbar.output_options()
        enabled = [name for name, flag in opts.items() if flag]
        self._log(f"附加输出选项: {', '.join(enabled) if enabled else 'None'}")
