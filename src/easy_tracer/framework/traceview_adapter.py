import time
from easy_tracer.framework import subprocess_utils


class TraceviewAdapter:
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path

    def start_tracing(
        self,
        device_serial: str,
        package_name: str,
        sampling: bool = False,
        sampling_interval: int = 1000,
    ):
        """Starts method tracing for the specified package."""
        trace_file = f"/data/local/tmp/{package_name}.trace"

        cmd = [self.adb_path, "-s", device_serial, "shell", "am", "profile", "start"]

        if sampling:
            cmd.extend(["--sampling", str(sampling_interval)])

        cmd.extend([package_name, trace_file])

        out = subprocess_utils.check_output(cmd)
        # am profile 通常无输出；保留 out 以便排障

    def stop_tracing(
        self, device_serial: str, package_name: str, output_path: str
    ) -> str:
        """Stops method tracing and pulls the trace file."""
        # Stop profiling
        subprocess_utils.check_output(
            [
                self.adb_path,
                "-s",
                device_serial,
                "shell",
                "am",
                "profile",
                "stop",
                package_name,
            ]
        )

        # Give Android a moment to flush the file
        time.sleep(1)

        device_trace_file = f"/data/local/tmp/{package_name}.trace"

        # Pull file
        subprocess_utils.check_output(
            [
                self.adb_path,
                "-s",
                device_serial,
                "pull",
                device_trace_file,
                output_path,
            ]
        )

        # Cleanup
        try:
            subprocess_utils.check_output(
                [self.adb_path, "-s", device_serial, "shell", "rm", device_trace_file]
            )
        except Exception:
            pass

        return output_path
