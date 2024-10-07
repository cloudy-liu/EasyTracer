import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog

from views.systrace_advanced_dialog import SystraceAdvancedDialog


class MainView(QtWidgets.QMainWindow):
    """Main view of the application."""

    start_trace_signal = pyqtSignal(dict)
    stop_trace_signal = pyqtSignal()
    open_output_signal = pyqtSignal(Path)

    def __init__(self) -> None:
        """Initialize the main view."""
        super().__init__()
        uic.loadUi('ui/main_window.ui', self)
        self.setup_ui()
        
        # Add fake atrace categories for testing
        self.atrace_categories: List[str] = [
            "gfx", "input", "view", "webview", "wm", "am", "sm", "audio", "video",
            "camera", "hal", "app", "res", "dalvik", "rs", "bionic", "power",
            "pm", "ss", "database", "network", "adb", "vibrator", "aidl",
            "nnapi", "rro", "binder_driver", "binder_lock"
        ]
        self.selected_atrace_categories: List[str] = self.atrace_categories.copy()  # 初始化为所有类别
        self.selected_ftrace_options: List[str] = []
        self.trace_commands: Dict[str, str] = {'pre_command': '', 'post_command': ''}

    def setup_ui(self) -> None:
        """Set up the user interface."""
        self._connect_ui_elements()
        self._setup_device_combo()
        self._setup_tracer_type_combo()
        self._setup_trace_time_combo()
        self._setup_time_unit_combo()
        self._setup_buffer_size_input()
        self._setup_output_folder()

    def _connect_ui_elements(self) -> None:
        """Connect UI elements to their respective methods."""
        self.start_button.clicked.connect(self.on_start_clicked)
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.open_output_button.clicked.connect(self.on_open_output_clicked)
        self.clear_log_button.clicked.connect(self.clear_log)
        self.advanced_settings_button.clicked.connect(self.show_advanced_settings)

    def _setup_device_combo(self) -> None:
        """Set up the device combo box."""
        self.device_combo.addItems(['Device 1', 'Device 2', 'Device 3'])
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)

    def _setup_tracer_type_combo(self) -> None:
        """Set up the tracer type combo box."""
        self.tracer_type_combo.addItems(['systrace', 'perfetto'])

    def _setup_trace_time_combo(self) -> None:
        """Set up the trace time combo box."""
        self.trace_time_combo.addItems(['5', '10', '15', 'Custom'])
        self.trace_time_combo.setCurrentText('10')
        self.trace_time_combo.setPlaceholderText("Select or enter time")
        self.trace_time_combo.setEditable(True)
        self.trace_time_combo.currentIndexChanged.connect(self.on_trace_time_changed)
        self.trace_time_combo.lineEdit().editingFinished.connect(self.on_trace_time_edited)

    def _setup_time_unit_combo(self) -> None:
        """Set up the time unit combo box."""
        self.time_unit_combo.addItems(['s', 'min'])
        self.time_unit_combo.setCurrentText('s')
        self.time_unit_combo.setMinimumWidth(80)

    def _setup_buffer_size_input(self) -> None:
        """Set up the buffer size input and unit combo box."""
        self.buffer_size_input.setText('120')
        self.buffer_unit_combo.addItems(['KB', 'MB'])
        self.buffer_unit_combo.setCurrentText('MB')
        self.buffer_unit_combo.setMinimumWidth(80)

    def _setup_output_folder(self) -> None:
        """Set up the default output folder path."""
        self.output_folder_input.setText(str(Path.cwd()))

    def on_trace_time_changed(self, index: int) -> None:
        """Handle trace time combo box changes."""
        if self.trace_time_combo.currentText() == 'Custom':
            self.trace_time_combo.setCurrentText("")
            self.trace_time_combo.lineEdit().setFocus()

    def on_trace_time_edited(self) -> None:
        """Handle trace time combo box edits."""
        if self.trace_time_combo.currentText() == "":
            self.trace_time_combo.setCurrentIndex(self.trace_time_combo.findText('Custom'))

    def on_device_changed(self, index: int) -> None:
        """Update atrace categories when device changes."""
        self.atrace_categories = [f"Category {i}" for i in range(1, 21)]

    def show_advanced_settings(self) -> None:
        """Show advanced settings dialog."""
        if self.tracer_type_combo.currentText() == 'systrace':
            dialog = SystraceAdvancedDialog(self)
            dialog.set_categories(self.atrace_categories, self.selected_atrace_categories)
            dialog.setModal(True)  # Ensure the dialog is modal
            if dialog.exec_() == QDialog.Accepted:
                self.selected_atrace_categories = dialog.get_selected_categories()
                self.selected_ftrace_options = dialog.get_ftrace_options()
                self.trace_commands = dialog.get_commands()
                
                categories_str = ', '.join(self.selected_atrace_categories) if self.selected_atrace_categories else "None"
                ftrace_str = ', '.join(self.selected_ftrace_options) if self.selected_ftrace_options else "None"
                
                self.update_log(f"Selected atrace categories: {categories_str}")
                self.update_log(f"Selected ftrace options: {ftrace_str}")
                self.update_log(f"Pre-trace command: {self.trace_commands['pre_command']}")
                self.update_log(f"Post-trace command: {self.trace_commands['post_command']}")
            else:
                self.update_log("Advanced settings were not changed.")
        else:
            # TODO: Implement perfetto advanced settings
            pass

    def on_start_clicked(self) -> None:
        """Handle start button click."""
        trace_config = self._get_trace_config()
        
        if not self._validate_trace_time(trace_config['trace_time']):
            return

        config_str = self._format_config_string(trace_config)
        print(config_str)
        self.update_log(config_str)

        self.start_trace_signal.emit(trace_config)

    def _get_trace_config(self) -> Dict[str, Any]:
        """Get the current trace configuration."""
        return {
            'device': self.device_combo.currentText(),
            'tracer_type': self.tracer_type_combo.currentText(),
            'trace_time': self.trace_time_combo.currentText(),
            'time_unit': self.time_unit_combo.currentText(),
            'buffer_size': self.buffer_size_input.text(),
            'buffer_unit': self.buffer_unit_combo.currentText(),
            'output_folder': str(Path(self.output_folder_input.text())),
            'advanced_settings': {
                'categories': self.selected_atrace_categories,
                'ftrace_options': self.selected_ftrace_options,
                'pre_command': self.trace_commands['pre_command'],
                'post_command': self.trace_commands['post_command']
            }
        }

    def _validate_trace_time(self, trace_time: str) -> bool:
        """Validate the trace time input."""
        try:
            float(trace_time)
            return True
        except ValueError:
            self.show_error("Please enter a valid number for trace time.")
            return False

    def _format_config_string(self, trace_config: Dict[str, Any]) -> str:
        """Format the configuration string for logging."""
        advanced_settings = trace_config.get('advanced_settings', {})
        categories = ', '.join(advanced_settings.get('categories', []))
        return (
            f"user config : device='{trace_config['device']}', "
            f"type='{trace_config['tracer_type']}', "
            f"time='{trace_config['trace_time']}{trace_config['time_unit']}', "
            f"buffer: {trace_config['buffer_size']}{trace_config['buffer_unit']}, "
            f"Advanced setting: atrace category: {categories}"
        )

    def on_open_output_clicked(self) -> None:
        """Handle open output folder button click."""
        output_folder = Path(self.output_folder_input.text())
        self.open_output_signal.emit(output_folder)

    def update_log(self, message: str) -> None:
        """Update the log output."""
        self.log_output.appendPlainText(message)

    def show_error(self, message: str) -> None:
        """Show an error message."""
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def show_success(self, message: str) -> None:
        """Show a success message."""
        QtWidgets.QMessageBox.information(self, "Success", message)

    def clear_log(self) -> None:
        """Clear the log output."""
        self.log_output.clear()

    def update_device_list(self, devices: List[str]) -> None:
        """Update the device list in the combo box."""
        self.device_combo.clear()
        self.device_combo.addItems(devices)

    def on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.stop_trace_signal.emit()
        self.update_log("Trace stopped.")