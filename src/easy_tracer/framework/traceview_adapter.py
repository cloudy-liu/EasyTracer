"""Traceview (method tracing) adapter.

Delegates all ADB operations to adb_helper for unified resource management.
"""

import time

from easy_tracer.framework import adb_helper


class TraceviewAdapter:
    def __init__(
        self,
        adb: adb_helper.AdbHelper | None = None,
        adb_path: str = "adb",
    ):
        self.adb = adb if adb else adb_helper.AdbHelper(adb_path)

    def start_tracing(
        self,
        device_serial: str,
        package_name: str,
        sampling: bool = False,
        sampling_interval: int = 1000,
    ):
        """Starts method tracing for the specified package."""
        trace_file = f"/data/local/tmp/{package_name}.trace"

        cmd_parts = ["am", "profile", "start"]
        if sampling:
            cmd_parts.extend(["--sampling", str(sampling_interval)])
        cmd_parts.extend([package_name, trace_file])

        self.adb.run_shell(device_serial, *cmd_parts)

    def stop_tracing(
        self, device_serial: str, package_name: str, output_path: str
    ) -> str:
        """Stops method tracing and pulls the trace file."""
        self.adb.run_shell(device_serial, "am", "profile", "stop", package_name)

        # Give Android a moment to flush the file
        time.sleep(1)

        device_trace_file = f"/data/local/tmp/{package_name}.trace"
        self.adb.pull_file(device_serial, device_trace_file, output_path)
        self.adb.remove_file(device_serial, device_trace_file)

        return output_path
