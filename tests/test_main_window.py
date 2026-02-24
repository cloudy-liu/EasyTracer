from unittest.mock import MagicMock, patch

from easy_tracer.models.device import Device
from easy_tracer.ui import main_window as main_window_module
from easy_tracer.ui.main_window import MainWindow


class _FakePanel:
    def __init__(self):
        self.updated_serials = []

    def update_device(self, serial):
        self.updated_serials.append(serial)


def test_on_device_changed_updates_current_panel_only_once_when_same_instance():
    panel = _FakePanel()
    window = MainWindow.__new__(MainWindow)
    window.presenter = MagicMock()
    window.device_panel = MagicMock()
    window.stack = MagicMock()
    window.stack.currentWidget.return_value = panel
    window.systrace_panel = panel
    window.perfetto_panel = None
    window.simpleperf_panel = None
    window.traceview_panel = None
    window.combo_panel = None

    selected = Device(serial="c8569b3d", status="device", model="PHB110")
    MainWindow._on_device_changed(window, selected)

    assert panel.updated_serials == ["c8569b3d"]


def test_update_record_button_state_when_not_ready():
    window = MainWindow.__new__(MainWindow)
    window.record_button = MagicMock()
    window._set_record_button_visuals = MagicMock()
    window._current_ready = False
    window._current_busy = False

    MainWindow._update_record_button_state(window)

    window.record_button.setEnabled.assert_called_once_with(False)
    window._set_record_button_visuals.assert_called_once_with(is_recording=False)


def test_update_record_button_state_when_ready():
    window = MainWindow.__new__(MainWindow)
    window.record_button = MagicMock()
    window._set_record_button_visuals = MagicMock()
    window._current_ready = True
    window._current_busy = False

    MainWindow._update_record_button_state(window)

    window.record_button.setEnabled.assert_called_once_with(True)
    window._set_record_button_visuals.assert_called_once_with(is_recording=False)


def test_update_record_button_state_when_busy():
    window = MainWindow.__new__(MainWindow)
    window.record_button = MagicMock()
    window._set_record_button_visuals = MagicMock()
    window._current_ready = False
    window._current_busy = True

    MainWindow._update_record_button_state(window)

    window.record_button.setEnabled.assert_called_once_with(True)
    window._set_record_button_visuals.assert_called_once_with(is_recording=True)


def test_global_record_click_starts_when_not_busy():
    class _FakePanel:
        def __init__(self):
            self.started = False
            self.stopped = False

        def start_capture(self):
            self.started = True

        def stop_capture(self):
            self.stopped = True

    panel = _FakePanel()
    window = MainWindow.__new__(MainWindow)
    window.stack = MagicMock()
    window.stack.currentWidget.return_value = panel
    window._current_busy = False

    with patch.object(main_window_module, "BasePanel", _FakePanel):
        MainWindow._on_global_record_clicked(window)

    assert panel.started is True
    assert panel.stopped is False


def test_global_record_click_stops_when_busy():
    class _FakePanel:
        def __init__(self):
            self.started = False
            self.stopped = False

        def start_capture(self):
            self.started = True

        def stop_capture(self):
            self.stopped = True

    panel = _FakePanel()
    window = MainWindow.__new__(MainWindow)
    window.stack = MagicMock()
    window.stack.currentWidget.return_value = panel
    window._current_busy = True

    with patch.object(main_window_module, "BasePanel", _FakePanel):
        MainWindow._on_global_record_clicked(window)

    assert panel.started is False
    assert panel.stopped is True
