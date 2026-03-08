from pathlib import Path

from easy_tracer.main import _get_app_root as get_gui_app_root
from easy_tracer.cli.main import _get_app_root as get_cli_app_root


def test_gui_app_root_points_to_repo_root():
    expected = Path(__file__).resolve().parents[1]
    assert get_gui_app_root() == expected


def test_cli_app_root_points_to_repo_root():
    expected = Path(__file__).resolve().parents[1]
    assert get_cli_app_root() == expected


def test_runtime_context_uses_single_adb_instance(temp_output_dir):
    from easy_tracer.runtime import build_runtime_context

    context = build_runtime_context(adb_path="adb", output_dir=temp_output_dir)

    assert context.capture_service.adb_helper is context.adb
    assert context.capture_service.systrace_adapter.adb is context.adb
    assert context.simpleperf_service.simpleperf_adapter.adb is context.adb
    assert context.perfetto_service.perfetto_adapter.adb is context.adb
    assert context.traceview_service.adapter.adb is context.adb


def test_resolve_device_prefers_ready_devices():
    from easy_tracer.runtime import resolve_target_device
    from easy_tracer.models.device import Device

    devices = [
        Device(serial="offline-1", status="offline"),
        Device(serial="ready-1", status="device"),
        Device(serial="unauth-1", status="unauthorized"),
    ]

    assert resolve_target_device(devices, requested_serial=None) == "ready-1"

