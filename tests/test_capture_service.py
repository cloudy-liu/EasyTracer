import os
from unittest.mock import MagicMock, patch

from easy_tracer.services.capture_service import CaptureService


def test_start_capture_uses_model_sdk_filename_format(temp_output_dir):
    adapter = MagicMock()
    adapter.get_device_model.return_value = "PHB110"
    adapter.get_device_sdk_version.return_value = 36

    service = CaptureService(adapter, output_dir=temp_output_dir)

    with patch(
        "easy_tracer.services.capture_service.time.strftime",
        return_value="20260214-203724",
    ):
        output_path = service.start_capture(
            device_serial="c8569b3d",
            categories=["sched", "gfx"],
            duration_seconds=5,
            buffer_size_kb=10240,
            app_name=None,
        )

    assert os.path.basename(output_path) == "PHB110_36_systrace_20260214-203724.html"
    adapter.run_systrace.assert_called_once()
