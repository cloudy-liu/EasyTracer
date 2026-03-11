from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from easy_tracer.models.requests import (
    ComboRequest,
    PerfettoRequest,
    SimpleperfRequest,
    SystraceRequest,
    TraceviewStartRequest,
)
from easy_tracer.presenters.combo_presenter import ComboPresenter
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.qt_threading import run_in_thread


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class ComboSettingsDialog(BaseSettingsDialog):
    """Lightweight settings dialog for combo captures."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, "Combo Settings")

        self.perfetto_mode = QtWidgets.QComboBox()
        self.perfetto_mode.addItems(["Normal", "Long"])
        self.add_row("Perfetto Mode:", self.perfetto_mode)

        self.simpleperf_freq = QtWidgets.QComboBox()
        self.simpleperf_freq.addItems(["500", "1000", "4000", "10000"])
        self.add_row("Simpleperf Freq:", self.simpleperf_freq)

        self.cold_start_cb = QtWidgets.QCheckBox("Cold Start (force-stop)")
        self.add_widget(self.cold_start_cb)


class ComboPanel(BasePanel):
    """Configuration panel for running multiple tracers in one capture."""

    def __init__(
        self,
        presenter: ComboPresenter,
        device_serial: Optional[str],
        default_output_dir: str,
    ):
        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self._auxiliary_options: Dict[str, bool] = {}

        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        self.duration_spin = QtWidgets.QSpinBox()
        self.duration_spin.setRange(1, 600)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" s")

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems([
            "All Apps (*)",
            "Top App (Foreground)",
            "Custom Package",
        ])

        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_input.setVisible(False)
        self.target_combo.currentTextChanged.connect(self._toggle_target_input)

        self.settings_dialog = ComboSettingsDialog(self)
        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self.settings_dialog.exec)

        self.output_path = OutputPathWidget(
            default_output_dir,
            label="",
            editable=True,
            tooltip="Shared output directory. Changes sync across panels.",
        )

        self.open_output_btn = QtWidgets.QPushButton()
        self.open_output_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        self.open_output_btn.setToolTip("Open output directory")
        self.open_output_btn.setMaximumWidth(36)
        self.open_output_btn.clicked.connect(self._on_open_output)

        self.perfetto_cb = QtWidgets.QCheckBox("Perfetto")
        self.simpleperf_cb = QtWidgets.QCheckBox("Simpleperf")
        self.systrace_cb = QtWidgets.QCheckBox("Systrace")
        self.traceview_cb = QtWidgets.QCheckBox("Traceview")
        self.perfetto_cb.setChecked(True)
        self.simpleperf_cb.setChecked(True)

        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setReadOnly(True)

        self._build_layout()
        self.update_device(self.device_serial)

    def _build_layout(self) -> None:
        """Builds the combo configuration layout."""

        target_layout = QtWidgets.QHBoxLayout()
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(8)
        target_layout.addWidget(self.target_combo)
        target_layout.addWidget(self.target_input)

        target_widget = QtWidgets.QWidget()
        target_widget.setLayout(target_layout)

        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(QtWidgets.QLabel("Duration:"))
        row1.addWidget(self.duration_spin)
        row1.addWidget(QtWidgets.QLabel("Target:"))
        row1.addWidget(target_widget, 1)
        row1.addWidget(QtWidgets.QLabel("Output:"))
        row1.addWidget(self.output_path, 1)
        row1.addWidget(self.open_output_btn)
        row1.addWidget(self.settings_btn)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("Tools:"))
        row2.addWidget(self.perfetto_cb)
        row2.addWidget(self.simpleperf_cb)
        row2.addWidget(self.systrace_cb)
        row2.addWidget(self.traceview_cb)
        row2.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Combo Configuration"))
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addWidget(QtWidgets.QLabel("Results"))
        layout.addWidget(self.result_text, 1)

    def _toggle_target_input(self, _text: str) -> None:
        is_custom = self._is_custom_target_selected()
        self.target_input.setEnabled(is_custom)
        self.target_input.setVisible(is_custom)

    def _is_custom_target_selected(self) -> bool:
        """Returns whether the custom-package target is selected."""

        return self.target_combo.currentIndex() == self.target_combo.count() - 1

    def set_auxiliary_options(self, options: Dict[str, bool]) -> None:
        """Stores auxiliary output options from the main window."""

        self._auxiliary_options = options

    def _on_open_output(self) -> None:
        """Opens the output directory in the desktop file manager."""

        output_dir = self.output_path.output_dir()
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(output_dir))

    def update_device(self, serial: Optional[str]) -> None:
        """Updates the selected device and refreshes readiness state."""

        self.device_serial = serial
        self.readiness_changed.emit(self.is_ready())
        if serial:
            self.status_message.emit(f"Selected device: {serial}")
        else:
            self.status_message.emit("Please select a device.")

    def is_ready(self) -> bool:
        """Returns whether combo capture can start."""

        return bool(self.device_serial) and not self.presenter.is_running

    def update_view(self) -> None:
        """Refreshes UI state from the presenter."""

        busy = self.presenter.is_running
        self.busy_changed.emit(busy)
        self.readiness_changed.emit(self.is_ready())

        if busy:
            self.status_message.emit("Combo capture running...")
        else:
            self.status_message.emit("Ready.")

        if self.presenter.error_message:
            self.error_message.emit(self.presenter.error_message)

        if self.presenter.results:
            lines = [f"{key}: {value}" for key, value in self.presenter.results.items()]
            self.result_text.setPlainText("\n".join(lines))

    def _target_package(self) -> Optional[str]:
        if self._is_custom_target_selected():
            return self.target_input.text().strip() or None
        return None

    def _build_request(self) -> ComboRequest:
        """Builds a combo request from the current UI state."""

        output_dir = self.output_path.output_dir()
        package_name = self._target_package()
        duration = int(self.duration_spin.value())

        return ComboRequest(
            device_serial=self.device_serial or "",
            duration_seconds=duration,
            output_dir=output_dir,
            systrace=(
                SystraceRequest(
                    device_serial=self.device_serial or "",
                    categories=["sched", "gfx", "view", "wm", "am"],
                    duration_seconds=duration,
                    app_name=package_name,
                    output_dir=output_dir,
                )
                if self.systrace_cb.isChecked()
                else None
            ),
            perfetto=(
                PerfettoRequest(
                    device_serial=self.device_serial or "",
                    duration_seconds=duration,
                    output_dir=output_dir,
                )
                if self.perfetto_cb.isChecked()
                else None
            ),
            simpleperf=(
                SimpleperfRequest(
                    device_serial=self.device_serial or "",
                    app_name=package_name,
                    duration_seconds=duration,
                    frequency=int(self.settings_dialog.simpleperf_freq.currentText()),
                    cold_start=self.settings_dialog.cold_start_cb.isChecked(),
                    output_dir=output_dir,
                )
                if self.simpleperf_cb.isChecked()
                else None
            ),
            traceview=(
                TraceviewStartRequest(
                    device_serial=self.device_serial or "",
                    package_name=package_name,
                    output_dir=output_dir,
                )
                if self.traceview_cb.isChecked() and package_name
                else None
            ),
            auxiliary_options=self._auxiliary_options,
        )

    def start_capture(self) -> None:
        """Starts a combo capture when the panel is ready."""

        if not self.is_ready():
            return

        request = self._build_request()
        run_in_thread(self.presenter.run_request, request)
        self.capture_started.emit(request.duration_seconds)
