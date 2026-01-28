import subprocess
import time
from easy_tracer.framework.subprocess_utils import subprocess_hidden_window_kwargs


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

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to start Traceview: {e.stderr if e.stderr else e.stdout}"
            ) from e

    def stop_tracing(
        self, device_serial: str, package_name: str, output_path: str
    ) -> str:
        """Stops method tracing and pulls the trace file."""
        # Stop profiling
        try:
            subprocess.run(
                [
                    self.adb_path,
                    "-s",
                    device_serial,
                    "shell",
                    "am",
                    "profile",
                    "stop",
                    package_name,
                ],
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to stop Traceview: {e.stderr}") from e

        # Give Android a moment to flush the file
        time.sleep(1)

        device_trace_file = f"/data/local/tmp/{package_name}.trace"

        # Pull file
        try:
            subprocess.run(
                [
                    self.adb_path,
                    "-s",
                    device_serial,
                    "pull",
                    device_trace_file,
                    output_path,
                ],
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to pull trace file: {e.stderr}") from e

        # Cleanup
        try:
            subprocess.run(
                [self.adb_path, "-s", device_serial, "shell", "rm", device_trace_file],
                capture_output=True,
                check=False,
                **subprocess_hidden_window_kwargs(),
            )
        except Exception:
            pass

        return output_path
