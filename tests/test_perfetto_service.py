from unittest.mock import MagicMock

from easy_tracer.models.requests import PerfettoRequest
from easy_tracer.services.perfetto_service import PerfettoService


def test_perfetto_service_applies_atrace_app_scope_to_preset_config(tmp_path):
    adapter = MagicMock()
    service = PerfettoService(adapter, output_dir=str(tmp_path))

    request = PerfettoRequest(
        device_serial="SER123",
        duration_seconds=10,
        preset="standard",
        output_dir=str(tmp_path),
        atrace_apps=["com.android.settings"],
    )

    service.run(request)

    kwargs = adapter.record_trace.call_args.kwargs
    assert 'atrace_apps: "com.android.settings"' in kwargs["config_text"]
    assert 'atrace_apps: "*"' not in kwargs["config_text"]
