from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6 import QtWidgets

from easy_tracer.models.device import Device
from easy_tracer.ui import main_window as main_window_module
from easy_tracer.ui.main_window import MainWindow
from easy_tracer.ui.panels import systrace_panel as systrace_panel_module
from easy_tracer.ui.panels.systrace_panel import SystracePanel


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


def test_systrace_panel_output_path_is_editable(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None

    presenter = SimpleNamespace(
        bind_view_update=lambda callback: None,
        is_loading_categories=False,
        is_capturing=False,
        categories=[],
        error_message=None,
        last_output_path=None,
        load_categories=lambda serial: None,
        run_request=lambda request: None,
    )
    monkeypatch.setattr(systrace_panel_module, "run_in_thread", lambda fn, *args: None)

    panel = SystracePanel(presenter, "SER123", "output")

    assert panel.output_path.path_input.isReadOnly() is False


def test_on_shared_output_dir_changed_updates_config_and_runtime():
    class _ConfigService:
        def __init__(self):
            self.adb_path = "adb"
            self.output_dir = "output"

        def update(self, adb_path: str, output_dir: str) -> None:
            self.adb_path = adb_path
            self.output_dir = output_dir

    window = MainWindow.__new__(MainWindow)
    window.config_service = _ConfigService()
    window.settings_panel = SimpleNamespace(output_input=MagicMock())
    window.systrace_presenter = SimpleNamespace(capture_service=SimpleNamespace(output_dir="output"))
    window.perfetto_presenter = SimpleNamespace(perfetto_service=SimpleNamespace(output_dir="output"))
    window.simpleperf_presenter = SimpleNamespace(simpleperf_service=SimpleNamespace(output_dir="output"))
    window.traceview_presenter = SimpleNamespace(traceview_service=SimpleNamespace(output_dir="output"))
    window.combo_presenter = SimpleNamespace(combo_service=SimpleNamespace(output_dir="output"))
    window.systrace_panel = None
    window.perfetto_panel = None
    window.simpleperf_panel = None
    window.traceview_panel = None
    window.combo_panel = None
    window._log = MagicMock()

    MainWindow._on_shared_output_dir_changed(window, "new-output")

    window.settings_panel.output_input.setText.assert_called_once_with("new-output")
    assert window.systrace_presenter.capture_service.output_dir == "new-output"
    assert window.perfetto_presenter.perfetto_service.output_dir == "new-output"
    assert window.simpleperf_presenter.simpleperf_service.output_dir == "new-output"
    assert window.traceview_presenter.traceview_service.output_dir == "new-output"
    assert window.combo_presenter.combo_service.output_dir == "new-output"
    window._log.assert_called_once()
