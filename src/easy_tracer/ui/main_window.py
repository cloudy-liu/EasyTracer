from __future__ import annotations

import logging
from typing import Callable, List, Optional

from PySide6 import QtCore, QtWidgets, QtGui
from easy_tracer.assets import load_icon
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
from easy_tracer.ui.theme import record_button_qss, Dimensions, Colors, Spacing, Typography
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
        self.setWindowIcon(load_icon("app", size=64))
        self.resize(1100, 780)

        # Global record button: idle=record(green), busy=stop(red).
        self.record_button = QtWidgets.QPushButton("录制")
        self.record_button.setMinimumWidth(Dimensions.BUTTON_RECORD_WIDTH)
        self.record_button.clicked.connect(self._on_global_record_clicked)
        self.record_button.setEnabled(False)
        self._set_record_button_visuals(is_recording=False)

        # Toolbar — single container so QToolBar doesn't spread items apart.
        self.toolbar = QtWidgets.QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {Colors.NEUTRAL_100};
                border-bottom: 1px solid {Colors.NEUTRAL_300};
                spacing: 0;
            }}
        """)
        self.addToolBar(self.toolbar)

        self.device_toolbar = DeviceToolbar()
        self.device_toolbar.refresh_requested.connect(self.refresh_devices)
        self.device_toolbar.device_changed.connect(self._on_device_changed)
        self.device_toolbar.options_changed.connect(self._on_options_changed)

        toolbar_container = QtWidgets.QWidget()
        tc_layout = QtWidgets.QHBoxLayout(toolbar_container)
        tc_layout.setContentsMargins(Spacing.XL, Spacing.MD, Spacing.XL, Spacing.MD)
        tc_layout.setSpacing(Spacing.LG)
        tc_layout.addWidget(self.device_toolbar)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setFixedHeight(28)
        sep.setStyleSheet(f"background-color: {Colors.NEUTRAL_300};")
        tc_layout.addWidget(sep)

        tc_layout.addWidget(self.record_button)
        tc_layout.addStretch(1)
        self.toolbar.addWidget(toolbar_container)

        # Status Bar
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_progress = QtWidgets.QProgressBar()
        self.status_progress.setMaximumWidth(200)
        self.status_progress.setVisible(False)
        self.status_progress.setRange(0, 0)  # Indeterminate
        self.status_bar.addPermanentWidget(self.status_progress)

        # Countdown timer drives determinate progress during timed captures.
        self._countdown_timer = QtCore.QTimer()
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)
        self._capture_duration = 0
        self._capture_elapsed = 0

        self.nav_list = QtWidgets.QListWidget()
        self.nav_list.setMinimumWidth(160)
        self.nav_list.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Expanding,
        )

        # Sidebar-specific styling: flat left-border indicator, no rounded frame.
        self.nav_list.setStyleSheet(f"""
            QListWidget {{
                border: none;
                border-right: 1px solid {Colors.NEUTRAL_300};
                border-radius: 0;
                background-color: {Colors.SURFACE};
                outline: none;
            }}
            QListWidget::item {{
                padding: {Spacing.MD}px {Spacing.XL}px;
                border-left: 3px solid transparent;
            }}
            QListWidget::item:hover {{
                background-color: {Colors.NEUTRAL_100};
            }}
            QListWidget::item:selected {{
                background-color: #e3f2fd;
                color: {Colors.PRIMARY_DARK};
                font-weight: 600;
                border-left: 3px solid {Colors.PRIMARY};
            }}
        """)

        # Build grouped navigation sidebar.
        # Tuples: (label, icon_name, stack_index).  Stack indices are fixed by
        # the order in which widgets are added to QStackedWidget (see below).
        self._nav_to_stack: dict[int, int] = {}
        self._stack_to_nav: dict[int, int] = {}
        nav_sections = [
            ("Tracers", [
                ("Systrace", "systrace", 1),
                ("Perfetto", "perfetto", 2),
                ("Simpleperf", "simpleperf", 3),
                ("Traceview", "traceview", 4),
                ("Combo", "combo", 5),
            ]),
            ("System", [
                ("Device", "device", 0),
                ("Settings", "settings", 6),
                ("About", "about", 7),
            ]),
        ]
        nav_row = 0
        for section_title, items in nav_sections:
            if section_title:
                header = QtWidgets.QListWidgetItem(f"  {section_title.upper()}")
                header.setFlags(QtCore.Qt.NoItemFlags)
                font = header.font()
                font.setPointSize(max(font.pointSize() - 2, 7))
                font.setBold(True)
                header.setFont(font)
                header.setForeground(QtGui.QColor(Colors.NEUTRAL_500))
                self.nav_list.addItem(header)
                nav_row += 1
            for label, icon_name, stk_idx in items:
                icon = load_icon(icon_name)
                item = QtWidgets.QListWidgetItem(icon, label)
                item.setData(QtCore.Qt.UserRole, label)
                self.nav_list.addItem(item)
                self._nav_to_stack[nav_row] = stk_idx
                self._stack_to_nav[stk_idx] = nav_row
                nav_row += 1

        self.stack = QtWidgets.QStackedWidget()

        # Panels are created lazily to reduce cold-start time of the packaged EXE.
        # Stack indices: 0 Device, 1 Systrace, 2 Perfetto, 3 Simpleperf,
        #                4 Traceview, 5 Combo, 6 Settings, 7 About
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
        self.nav_list.setCurrentRow(self._stack_to_nav.get(0, 0))

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
        """Ensure the panel widget for a given stack index exists.

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

        # Connect busy badge to sidebar — persists across panel switches.
        if isinstance(panel, BasePanel):
            nav_row = self._stack_to_nav.get(index)
            if nav_row is not None:
                panel.busy_changed.connect(
                    lambda busy, r=nav_row: self._update_nav_badge(r, busy)
                )

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
        panel.set_auxiliary_options(self.device_toolbar.output_options())
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
        panel.set_auxiliary_options(self.device_toolbar.output_options())
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
        panel.set_auxiliary_options(self.device_toolbar.output_options())
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
        panel.set_auxiliary_options(self.device_toolbar.output_options())
        self._bind_shared_output_dir(panel)
        self.combo_panel = panel
        return panel

    def _bind_shared_output_dir(self, panel: QtWidgets.QWidget) -> None:
        output_path = getattr(panel, "output_path", None)
        if output_path is None or not hasattr(output_path, "output_dir_changed"):
            return
        output_path.output_dir_changed.connect(self._on_shared_output_dir_changed)

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

        stack_idx = self._nav_to_stack.get(index)
        if stack_idx is None:
            return  # Section header — not navigable

        # Disconnect old panel signals if it was a BasePanel
        current = self.stack.currentWidget()
        if isinstance(current, BasePanel):
            try:
                current.readiness_changed.disconnect(self._update_start_button)
                current.busy_changed.disconnect(self._update_busy_state)
                current.status_message.disconnect(self.status_bar.showMessage)
                current.error_message.disconnect(self._show_error)
                current.capture_started.disconnect(self._on_capture_started)
            except RuntimeError:
                pass  # Already disconnected or destroyed

        new_panel = self._ensure_panel(stack_idx)
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
            new_panel.capture_started.connect(self._on_capture_started)

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
        if busy and self._capture_duration > 0:
            self.status_progress.setRange(0, self._capture_duration)
            self.status_progress.setValue(0)
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

    def _update_nav_badge(self, row: int, busy: bool) -> None:
        item = self.nav_list.item(row)
        if item is None:
            return
        base_text = item.data(QtCore.Qt.UserRole)
        if base_text is None:
            return
        if busy:
            item.setText(f"\u25cf {base_text}")
            item.setForeground(QtGui.QColor(Colors.SUCCESS))
        else:
            item.setText(base_text)
            item.setForeground(QtGui.QColor(Colors.NEUTRAL_800))

    def _on_countdown_tick(self) -> None:
        self._capture_elapsed += 1
        if self._capture_elapsed <= self._capture_duration:
            self.status_progress.setValue(self._capture_elapsed)
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

    def _apply_adb_path(self, adb_path: str) -> None:
        # Update adb path - all adapters share the same AdbHelper instance via device_service.
        # Updating it once propagates to all.
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

        # Combo uses sub-services, but keep its base dir consistent.
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
