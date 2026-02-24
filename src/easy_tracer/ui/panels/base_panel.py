from typing import Optional
from PySide6 import QtCore, QtWidgets

class BasePanel(QtWidgets.QWidget):
    """
    Abstract base class for all tracing panels.
    Enforces the interface required by MainWindow's unified control.
    """
    # Signal to tell MainWindow if the 'Start' button should be enabled
    readiness_changed = QtCore.Signal(bool)

    # Signal to report status text to MainWindow (replacing local status labels)
    status_message = QtCore.Signal(str)

    # Signal to report detailed error text
    error_message = QtCore.Signal(str)

    # Signal to report busy state (for progress bar)
    busy_changed = QtCore.Signal(bool)

    def __init__(self):
        super().__init__()

    def update_device(self, serial: Optional[str]) -> None:
        """Called when the global device selection changes."""
        raise NotImplementedError

    def is_ready(self) -> bool:
        """Returns True if all conditions (device, config) are met to start."""
        return False

    def start_capture(self) -> None:
        """
        Called when the global 'Start' button is clicked.
        Should gather config and call the presenter.
        """
        raise NotImplementedError

    def stop_capture(self) -> None:
        """
        Called when the global 'Stop' button is clicked (if applicable).
        """
        pass

    def on_capture_state_changed(self, is_running: bool) -> None:
        """Called by presenter when capture starts/stops."""
        pass
