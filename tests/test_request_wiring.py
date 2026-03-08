from types import SimpleNamespace
from unittest.mock import MagicMock
from pathlib import Path

from click.testing import CliRunner

from easy_tracer.cli.main import cli
from easy_tracer.models.device import Device
from easy_tracer.models.requests import ComboRequest, PerfettoRequest, TraceviewStartRequest
from easy_tracer.models.results import CaptureResult, ComboResult
from easy_tracer.presenters.combo_presenter import ComboPresenter
from easy_tracer.presenters.traceview_presenter import TraceviewPresenter
from easy_tracer.ui.panels import combo_panel as combo_panel_module
from easy_tracer.ui.panels import perfetto_panel as perfetto_panel_module
from easy_tracer.ui.panels.combo_panel import ComboPanel
from easy_tracer.ui.panels.perfetto_panel import PerfettoPanel


def _checkbox(checked: bool):
    return SimpleNamespace(isChecked=lambda: checked)


def _text_value(text: str):
    return SimpleNamespace(currentText=lambda: text)


def _spin_value(value: int):
    return SimpleNamespace(value=lambda: value)


def test_combo_cli_builds_shared_combo_request(monkeypatch):
    captured = {}

    class _FakeAdb:
        def is_available(self):
            return True

        def list_devices(self):
            return [Device(serial="SER123", status="device")]

    class _FakeComboService:
        def run(self, request):
            captured["request"] = request
            return ComboResult(status="success", files={"perfetto": "out/trace.perfetto-trace"})

    runtime = SimpleNamespace(adb=_FakeAdb(), combo_service=_FakeComboService())
    monkeypatch.setattr("easy_tracer.cli.main.build_runtime_context", lambda adb_path, output_dir: runtime)

    runner = CliRunner()
    result = runner.invoke(cli, ["combo", "--perfetto", "--simpleperf", "--logcat", "-d", "7"])

    assert result.exit_code == 0
    request = captured["request"]
    assert isinstance(request, ComboRequest)
    assert request.device_serial == "SER123"
    assert request.duration_seconds == 7
    assert request.perfetto is not None
    assert request.simpleperf is not None
    assert request.systrace is None
    assert request.traceview is None
    assert request.auxiliary_options["logcat"] is True
    assert request.auxiliary_options["packages"] is False


def test_perfetto_cli_passes_config_file_contents(monkeypatch, tmp_path):
    captured = {}

    class _FakeAdb:
        def is_available(self):
            return True

        def list_devices(self):
            return [Device(serial="SER123", status="device")]

    class _FakePerfettoService:
        def run(self, request):
            captured["request"] = request
            return CaptureResult(tool="perfetto", output_path="out/trace.perfetto-trace")

    runtime = SimpleNamespace(adb=_FakeAdb(), perfetto_service=_FakePerfettoService())
    monkeypatch.setattr("easy_tracer.cli.main.build_runtime_context", lambda adb_path, output_dir: runtime)

    config_path = tmp_path / "custom.pbtx"
    config_text = 'buffers { size_kb: 4096 fill_policy: RING_BUFFER }\nduration_ms: 2000\n'
    config_path.write_text(config_text, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["perfetto", "--config", str(config_path), "-d", "2"])

    assert result.exit_code == 0
    request = captured["request"]
    assert isinstance(request, PerfettoRequest)
    assert request.device_serial == "SER123"
    assert request.config_text == config_text
    assert request.categories is None
    assert request.preset is None


def test_perfetto_cli_strips_utf8_bom_from_config(monkeypatch, tmp_path):
    captured = {}

    class _FakeAdb:
        def is_available(self):
            return True

        def list_devices(self):
            return [Device(serial="SER123", status="device")]

    class _FakePerfettoService:
        def run(self, request):
            captured["request"] = request
            return CaptureResult(tool="perfetto", output_path="out/trace.perfetto-trace")

    runtime = SimpleNamespace(adb=_FakeAdb(), perfetto_service=_FakePerfettoService())
    monkeypatch.setattr("easy_tracer.cli.main.build_runtime_context", lambda adb_path, output_dir: runtime)

    config_path = tmp_path / "bom.pbtx"
    config_path.write_bytes("\ufeffbuffers { size_kb: 1024 fill_policy: RING_BUFFER }\n".encode("utf-8"))

    runner = CliRunner()
    result = runner.invoke(cli, ["perfetto", "--config", str(config_path)])

    assert result.exit_code == 0
    assert captured["request"].config_text.startswith("buffers {")


def test_perfetto_panel_start_capture_builds_perfetto_request(monkeypatch):
    presenter = MagicMock()
    presenter.is_recording = False

    panel = PerfettoPanel.__new__(PerfettoPanel)
    panel.presenter = presenter
    panel.device_serial = "SER123"
    panel._auxiliary_options = {"logcat": True}
    panel._current_preset = "custom"
    panel.output_path = SimpleNamespace(output_dir=lambda: "out")
    panel.capture_started = MagicMock()
    panel.settings_dialog = SimpleNamespace(
        buffer_combo=_text_value("64 MB"),
        write_period=_spin_value(2500),
        flush_period=_spin_value(30000),
    )
    panel.duration_combo = _text_value("10s")
    panel.atrace_checkboxes = {
        "gfx": _checkbox(True),
        "sched": _checkbox(True),
        "view": _checkbox(False),
    }
    panel.ds_ftrace = _checkbox(True)
    panel.ds_process_stats = _checkbox(True)
    panel.ds_sys_stats = _checkbox(True)
    panel.ds_system_info = _checkbox(False)
    panel.ds_surfaceflinger = _checkbox(True)
    panel.ds_gpu_memory = _checkbox(True)
    panel.ds_gpu_work = _checkbox(True)
    panel.ds_heapprofd = _checkbox(True)
    panel.ds_java_hprof = _checkbox(False)
    panel.ds_power = _checkbox(True)
    panel.ds_perf = _checkbox(True)
    panel.ds_packages_list = _checkbox(True)
    panel.ds_android_log = _checkbox(True)
    panel.ds_network = _checkbox(True)

    monkeypatch.setattr(perfetto_panel_module, "run_in_thread", lambda fn, *args: fn(*args))

    PerfettoPanel.start_capture(panel)

    presenter.run_request.assert_called_once()
    request = presenter.run_request.call_args.args[0]
    assert isinstance(request, PerfettoRequest)
    assert request.device_serial == "SER123"
    assert request.output_dir == "out"
    assert request.preset is None
    assert request.config is not None
    assert request.config.duration_ms == 10000
    assert request.config.buffer_size_kb == 64 * 1024
    assert request.config.atrace_categories == ["gfx", "sched"]
    assert request.config.enable_ftrace is True
    assert request.config.enable_surfaceflinger is True
    assert request.config.enable_gpu_memory is True
    assert request.config.enable_packages_list is True
    assert request.auxiliary_options == {"logcat": True}


def test_combo_panel_start_capture_builds_combo_request(monkeypatch):
    presenter = MagicMock()
    presenter.is_running = False

    panel = ComboPanel.__new__(ComboPanel)
    panel.presenter = presenter
    panel.device_serial = "SER123"
    panel._auxiliary_options = {"logcat": True, "packages": False}
    panel.output_path = SimpleNamespace(output_dir=lambda: "combo-out")
    panel.capture_started = MagicMock()
    panel.duration_spin = _spin_value(12)
    panel.perfetto_cb = _checkbox(True)
    panel.simpleperf_cb = _checkbox(True)
    panel.systrace_cb = _checkbox(True)
    panel.traceview_cb = _checkbox(True)
    panel.settings_dialog = SimpleNamespace(
        simpleperf_freq=_text_value("1000"),
        cold_start_cb=_checkbox(True),
        perfetto_mode=_text_value("Normal"),
    )
    panel._target_package = lambda: "com.example.app"

    monkeypatch.setattr(combo_panel_module, "run_in_thread", lambda fn, *args: fn(*args))

    ComboPanel.start_capture(panel)

    presenter.run_request.assert_called_once()
    request = presenter.run_request.call_args.args[0]
    assert isinstance(request, ComboRequest)
    assert request.device_serial == "SER123"
    assert request.duration_seconds == 12
    assert request.output_dir == "combo-out"
    assert request.systrace is not None
    assert request.perfetto is not None
    assert request.simpleperf is not None
    assert request.traceview is not None
    assert request.simpleperf.frequency == 1000
    assert request.simpleperf.cold_start is True
    assert request.traceview.package_name == "com.example.app"
    assert request.auxiliary_options["logcat"] is True


def test_traceview_presenter_uses_request_session_api():
    session = SimpleNamespace(
        stop=MagicMock(return_value=CaptureResult(tool="traceview", output_path="out/app.trace"))
    )
    service = SimpleNamespace(start_session=MagicMock(return_value=session))
    presenter = TraceviewPresenter(service)

    presenter.start_request(
        TraceviewStartRequest(
            device_serial="SER123",
            package_name="com.example.app",
            sampling=True,
            interval=500,
        )
    )

    assert presenter.is_tracing is True
    assert presenter.current_package == "com.example.app"

    presenter.stop_capture(output_dir="out")

    service.start_session.assert_called_once()
    session.stop.assert_called_once_with(output_dir="out")
    assert presenter.is_tracing is False
    assert presenter.current_package is None
    assert presenter.last_output_path == "out/app.trace"


def test_combo_presenter_preserves_partial_results():
    service = SimpleNamespace(
        run=MagicMock(
            return_value=ComboResult(
                status="partial",
                files={"perfetto": "out/trace.perfetto-trace"},
                errors={"simpleperf": "record failed"},
            )
        )
    )
    presenter = ComboPresenter(service)

    presenter.run_request(ComboRequest(device_serial="SER123", perfetto=PerfettoRequest(device_serial="SER123")))

    assert presenter.results == {"perfetto": "out/trace.perfetto-trace"}
    assert presenter.error_message == "simpleperf: record failed"
