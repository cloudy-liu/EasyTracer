import zlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def test_strip_and_decompress_trace_handles_compressed_bytes():
    # Atrace typically streams a zlib-compressed ftrace payload when -z is used.
    from easy_tracer.framework.external.systrace.agents.atrace_agent import (
        strip_and_decompress_trace,
    )

    trace_text = "# tracer: nop\n# test\n"
    compressed = zlib.compress(trace_text.encode("utf-8"))

    out = strip_and_decompress_trace(compressed)
    assert out.startswith("# tracer")
    assert "# test" in out


def test_atrace_agent_preprocess_accepts_bytes_chunks():
    # Regression test: keep compressed trace data as bytes all the way through
    # preprocessing, otherwise decompression will fail and the systrace HTML viewer
    # can't load the trace.
    from easy_tracer.framework.external.systrace.agents.atrace_agent import AtraceAgent

    options = SimpleNamespace(
        # We only exercise the decompression path here; avoid extra adb calls.
        fix_threads=False,
        fix_tgids=False,
        fix_circular=False,
        device_serial="TEST_SERIAL",
        adb_helper=None,
    )

    trace_text = "# tracer: nop\n# payload\n"
    compressed = zlib.compress(trace_text.encode("utf-8"))

    agent = AtraceAgent(options, categories=["sched"])
    out = agent._preprocess_trace_data([compressed])
    assert out.startswith("# tracer")
    assert "# payload" in out


def test_try_create_agent_passes_device_serial_to_sdk_lookup():
    from easy_tracer.framework.external.systrace.agents import atrace_agent

    mock_adb = MagicMock()
    mock_adb.get_sdk_version.return_value = 36

    options = SimpleNamespace(
        from_file=None,
        boot=False,
        device_serial="c8569b3d",
        adb_helper=mock_adb,
    )

    agent = atrace_agent.try_create_agent(options, categories=["sched"])

    mock_adb.get_sdk_version.assert_called_once_with("c8569b3d")
    assert agent is not None
