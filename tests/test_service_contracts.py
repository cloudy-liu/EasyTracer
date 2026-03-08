from pathlib import Path
from unittest.mock import MagicMock, patch


def test_capture_service_run_returns_structured_result(temp_output_dir):
    from easy_tracer.models.requests import SystraceRequest
    from easy_tracer.services.capture_service import CaptureService

    adapter = MagicMock()
    adapter.get_device_model.return_value = "PHB110"
    adapter.get_device_sdk_version.return_value = 36

    service = CaptureService(adapter, output_dir=temp_output_dir)

    request = SystraceRequest(
        device_serial="c8569b3d",
        categories=["sched", "gfx"],
        duration_seconds=5,
        buffer_size_kb=10240,
    )

    with patch(
        "easy_tracer.services.capture_service.time.strftime",
        return_value="20260214-203724",
    ):
        result = service.run(request)

    assert result.tool == "systrace"
    assert result.output_path.endswith("PHB110_36_systrace_20260214-203724.html")
    assert result.output_path == result.outputs["trace"]
    adapter.run_systrace.assert_called_once()


def test_traceview_service_start_session_returns_stoppable_handle(temp_output_dir):
    from easy_tracer.models.requests import TraceviewStartRequest
    from easy_tracer.services.traceview_service import TraceviewService

    adapter = MagicMock()
    adapter.stop_tracing.return_value = str(Path(temp_output_dir) / "traceview.trace")
    service = TraceviewService(adapter, output_dir=temp_output_dir)

    request = TraceviewStartRequest(
        device_serial="c8569b3d",
        package_name="com.android.settings",
        sampling=True,
        interval=1000,
    )

    with patch(
        "easy_tracer.services.traceview_service.time.strftime",
        return_value="20260214_203724",
    ):
        session = service.start_session(request)
        result = session.stop()

    adapter.start_tracing.assert_called_once_with(
        "c8569b3d", "com.android.settings", True, 1000
    )
    adapter.stop_tracing.assert_called_once()
    assert result.tool == "traceview"
    assert result.output_path == result.outputs["trace"]


def test_combo_service_run_returns_partial_result_instead_of_raising():
    from easy_tracer.models.requests import ComboRequest, SystraceRequest, PerfettoRequest
    from easy_tracer.services.combo_service import ComboService

    systrace = MagicMock()
    simpleperf = MagicMock()
    perfetto = MagicMock()
    traceview = MagicMock()

    systrace.run.return_value.output_path = "systrace.html"
    perfetto.run.side_effect = RuntimeError("perfetto boom")

    service = ComboService(systrace, simpleperf, perfetto, traceview, output_dir="output")
    request = ComboRequest(
        device_serial="c8569b3d",
        duration_seconds=5,
        systrace=SystraceRequest(
            device_serial="c8569b3d",
            categories=["sched", "gfx"],
            duration_seconds=5,
        ),
        perfetto=PerfettoRequest(
            device_serial="c8569b3d",
            duration_seconds=5,
            categories=["sched"],
        ),
    )

    result = service.run(request)

    assert result.files["systrace"] == "systrace.html"
    assert "perfetto" in result.errors
    assert result.status == "partial"
