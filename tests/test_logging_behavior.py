import io
import logging
import os
from unittest.mock import MagicMock, patch

from easy_tracer.framework import subprocess_utils
from easy_tracer.framework.systrace_adapter import SystraceAdapter, _TeeStream
from easy_tracer.services.capture_service import CaptureService


def test_check_output_logs_raw_command_at_debug_only(caplog):
    with patch(
        "easy_tracer.framework.subprocess_utils.subprocess.check_output",
        return_value="ok",
    ):
        with caplog.at_level(logging.INFO):
            output = subprocess_utils.check_output(["adb", "devices", "-l"])

    assert output == "ok"
    assert "Executing: adb devices -l" not in caplog.text

    caplog.clear()

    with patch(
        "easy_tracer.framework.subprocess_utils.subprocess.check_output",
        return_value="ok",
    ):
        with caplog.at_level(logging.DEBUG):
            subprocess_utils.check_output(["adb", "devices", "-l"])

    assert "Executing: adb devices -l" in caplog.text


def test_run_systrace_logs_concise_start_message(caplog):
    adapter = SystraceAdapter()

    with patch.object(adapter, "_import_and_run_systrace", return_value="done"):
        with caplog.at_level(logging.INFO):
            result = adapter.run_systrace(
                output_file="trace.html",
                time_seconds=5,
                device_serial="c8569b3d",
                categories=["sched", "gfx", "view"],
                buffer_size_kb=10240,
            )

    assert result == "done"
    assert "Starting systrace capture" in caplog.text
    assert "Atrace config:" in caplog.text
    assert "buffer=10240KB" in caplog.text
    assert "categories=sched gfx view" in caplog.text
    assert "Running systrace with args:" not in caplog.text


def test_tee_stream_capitalizes_wrote_file_prefix():
    original = io.StringIO()
    buffer = io.StringIO()
    stream = _TeeStream(original, buffer)

    stream.write("\n    wrote file://C:/trace.html\n")

    assert "Wrote file://C:/trace.html" in original.getvalue()
    assert "Wrote file://C:/trace.html" in buffer.getvalue()
    assert "wrote file://C:/trace.html" not in original.getvalue()


def test_dump_auxiliary_logs_logs_key_steps(temp_output_dir, caplog):
    adapter = MagicMock()
    adb_helper = MagicMock()
    service = CaptureService(adapter, output_dir=temp_output_dir, adb_helper=adb_helper)
    output_prefix = os.path.join(temp_output_dir, "capture")

    adb_helper.dump_logcat.side_effect = lambda serial, path: path
    adb_helper.dump_packages.side_effect = lambda serial, path: path

    with caplog.at_level(logging.INFO):
        results = service.dump_auxiliary_logs(
            device_serial="c8569b3d",
            output_prefix=output_prefix,
            options={"logcat": True, "packages": True},
        )

    assert results == {
        "logcat": output_prefix + "_logcat.txt",
        "packages": output_prefix + "_packages.txt",
    }
    assert "Dumping logcat..." in caplog.text
    assert f"Dumped logcat to {output_prefix}_logcat.txt" in caplog.text
    assert "Dumping packages..." in caplog.text
    assert f"Dumped packages to {output_prefix}_packages.txt" in caplog.text
