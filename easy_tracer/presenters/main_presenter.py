import os
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSlot


class MainPresenter(QObject):
    def __init__(self, view, model):
        super().__init__()
        self.view = view
        self.model = model
        self.view.presenter = self  # Add this line to create a reference to the presenter in the view

        # Connect view signals to presenter slots
        self.view.start_trace_signal.connect(self.start_trace)
        self.view.stop_trace_signal.connect(self.stop_trace)
        self.view.open_output_signal.connect(self.open_output_folder)

    @pyqtSlot(dict)
    def start_trace(self, trace_config):
        try:
            self.model.set_config(trace_config)
            result = self.model.start_trace()
            self.view.update_log(result)
        except Exception as e:
            self.view.show_error(str(e))

    @pyqtSlot()
    def stop_trace(self):
        try:
            result = self.model.stop_trace()
            self.view.update_log(result)
        except Exception as e:
            self.view.show_error(str(e))

    @pyqtSlot(Path)
    def open_output_folder(self, output_folder: Path):
        if output_folder.exists():
            os.startfile(str(output_folder))
        else:
            self.view.show_error(f"Output folder not found: {output_folder}")

    def update_log(self, message):
        self.view.update_log(message)

    # Remove other methods that interact with actual devices