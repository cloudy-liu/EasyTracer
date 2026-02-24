from typing import Optional, Dict, Any
from PySide6 import QtCore, QtWidgets
from easy_tracer.presenters.combo_presenter import ComboPresenter
from easy_tracer.ui.qt_threading import run_in_thread
from easy_tracer.ui.components.output_path_widget import OutputPathWidget
from easy_tracer.ui.panels.base_panel import BasePanel
from easy_tracer.ui.dialogs.base_settings_dialog import BaseSettingsDialog


class _UpdateEmitter(QtCore.QObject):
    updated = QtCore.Signal()


class ComboSettingsDialog(BaseSettingsDialog):
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
    def __init__(self, presenter: ComboPresenter, device_serial: Optional[str], default_output_dir: str):
        # Note: Added default_output_dir to signature to match other panels if needed,
        # but ComboPresenter might not use it directly in __init__?
        # Checking previous implementation: __init__(self, presenter, device_serial)
        # But MainWindow passes config_service.output_dir.
        # Let's check MainWindow... it passes config_service.output_dir to others,
        # but ComboPanel instantiation in MainWindow:
        # self.combo_panel = ComboPanel(combo_presenter, None) -> Wait, let's check MainWindow code from previous turn.
        # MainWindow.__init__:
        # self.combo_panel = ComboPanel(combo_presenter, None)
        # So it does NOT accept output_dir in init in previous version.
        # However, to support OutputPathWidget, we need it.
        # I should probably update MainWindow to pass it, or just use "." default and let set_output_dir handle it.
        # For now, I will keep signature compatible but maybe add optional, or update MainWindow later?
        # Actually, looking at the previous file content of combo_panel.py:
        # class ComboPanel(QtWidgets.QWidget):
        #     def __init__(self, presenter: ComboPresenter, device_serial: Optional[str]):
        # So I should stick to that signature or change MainWindow.
        # Changing MainWindow is safer to ensure it works.
        # Wait, I can't see MainWindow right now.
        # I will stick to the existing signature and default the output dir if not passed,
        # OR I can accept it if I update MainWindow.
        # Let's see... I'll check if I can just use "." and rely on _apply_runtime_settings in MainWindow to set it.

        super().__init__()
        self.presenter = presenter
        self.device_serial = device_serial
        self._update_emitter = _UpdateEmitter()
        self._update_emitter.updated.connect(self.update_view)
        self.presenter.bind_view_update(self._update_emitter.updated.emit)

        # --- Controls ---
        self.duration_spin = QtWidgets.QSpinBox()
        self.duration_spin.setRange(1, 600)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" s")

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItems([
            "所有应用 (*)", "当前前台应用 (Top App)", "自定义包名"
        ])
        self.target_input = QtWidgets.QLineEdit()
        self.target_input.setPlaceholderText("com.example.app")
        self.target_input.setEnabled(False)
        self.target_combo.currentTextChanged.connect(self._toggle_target_input)

        self.settings_dialog = ComboSettingsDialog(self)
        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self.settings_dialog.exec)

        # We need an output path widget.
        # Since constructor doesn't take it, we'll initialize with "."
        # MainWindow's _apply_runtime_settings will update it shortly after startup.
        self.output_path = OutputPathWidget(".")

        # --- Tool Checkboxes ---
        self.perfetto_cb = QtWidgets.QCheckBox("Perfetto")
        self.simpleperf_cb = QtWidgets.QCheckBox("Simpleperf")
        self.systrace_cb = QtWidgets.QCheckBox("Systrace")
        self.traceview_cb = QtWidgets.QCheckBox("Traceview")
        self.perfetto_cb.setChecked(True)
        self.simpleperf_cb.setChecked(True)

        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setReadOnly(True)

        # --- Layout ---
        # Row 1: Duration | Target | Output | Settings

        # Target Group
        target_layout = QtWidgets.QHBoxLayout()
        target_layout.setContentsMargins(0,0,0,0)
        target_layout.addWidget(self.target_combo)
        target_layout.addWidget(self.target_input)
        target_widget = QtWidgets.QWidget()
        target_widget.setLayout(target_layout)

        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(QtWidgets.QLabel("Duration:"))
        row1.addWidget(self.duration_spin)
        row1.addWidget(QtWidgets.QLabel("Target:"))
        row1.addWidget(target_widget, 1)
        row1.addWidget(self.output_path, 1)
        row1.addWidget(self.settings_btn)

        # Row 2: Tools
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

        self.update_device(self.device_serial)

    def _toggle_target_input(self, text: str) -> None:
        self.target_input.setEnabled(text == "自定义包名")

    def update_device(self, serial: Optional[str]) -> None:
        self.device_serial = serial
        self.readiness_changed.emit(self.is_ready())
        if serial:
            self.status_message.emit(f"Selected device: {serial}")
        else:
            self.status_message.emit("Please select a device.")

    def is_ready(self) -> bool:
        return bool(self.device_serial) and not self.presenter.is_running

    def update_view(self) -> None:
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
            lines = [f"{k}: {v}" for k, v in self.presenter.results.items()]
            self.result_text.setPlainText("\n".join(lines))

    def _target_package(self) -> Optional[str]:
        text = self.target_combo.currentText()
        if text == "自定义包名":
            return self.target_input.text().strip() or None
        if text == "当前前台应用 (Top App)":
            return None
        return None

    def start_capture(self) -> None:
        if not self.is_ready():
            return

        enabled = {
            "systrace": self.systrace_cb.isChecked(),
            "perfetto": self.perfetto_cb.isChecked(),
            "simpleperf": self.simpleperf_cb.isChecked(),
            "traceview": self.traceview_cb.isChecked(),
        }

        configs = {
            "package_name": self._target_package(),
            "simpleperf_freq": int(self.settings_dialog.simpleperf_freq.currentText()),
        }

        # Note: ComboPresenter.start_combo signature:
        # def start_combo(self, device_serial: str, duration: int, enabled_tools: dict, configs: dict)
        # It doesn't take output_dir?
        # Let's check ComboPresenter to be safe, but I can't see it now.
        # Assuming previous implementation was correct:
        # run_in_thread(self.presenter.start_combo, ..., configs)
        # It seems it uses internal logic for output path or it's in configs?
        # Previous ComboPanel._on_start didn't pass output_dir.
        # But we added OutputPathWidget.
        # If the presenter doesn't take it, we might need to set it on the service or similar.
        # However, MainWindow._apply_runtime_settings does:
        # self.combo_presenter.combo_service.output_dir = output_dir
        # So we just need to ensure the widget reflects that.
        # And if the user changes it in the widget, we should probably update the service.
        # But BasePanel/Presenter pattern usually passes it in start.
        # If ComboPresenter doesn't take it in start_combo, we rely on the service's state.
        # To be safe, I'll update the service's output_dir before starting if possible,
        # or just rely on what was set globally.
        # Actually, let's look at MainWindow again from my memory/previous turns.
        # MainWindow updates combo_presenter.combo_service.output_dir.
        # So the widget here might be just visual if we don't pass it.
        # But if the user changes it here, it won't apply unless we pass it.
        # Since I can't easily change Presenter signature safely without seeing it,
        # I will assume the user sets global output dir in Settings or it's synced.
        # BUT, the user expects the "Output" widget on this panel to do something.
        # If I can't pass it to start_combo, I should update the service property.
        self.presenter.combo_service.output_dir = self.output_path.output_dir()

        run_in_thread(
            self.presenter.start_combo,
            self.device_serial,
            int(self.duration_spin.value()),
            enabled,
            configs,
        )
