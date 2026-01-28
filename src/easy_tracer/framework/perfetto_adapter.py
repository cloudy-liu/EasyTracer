import subprocess
import time
from typing import List
from easy_tracer.framework.subprocess_utils import subprocess_hidden_window_kwargs


class PerfettoAdapter:
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path

    def record_trace(
        self,
        device_serial: str,
        output_path: str,
        duration_seconds: int = 10,
        categories: List[str] = None,
        buffer_size_kb: int = 32768,
    ) -> str:
        """
        Records a Perfetto trace on the device and pulls it to the local machine.
        Returns the local path to the trace file.
        """
        if categories is None:
            categories = [
                "sched",
                "gfx",
                "view",
                "wm",
                "am",
                "hal",
                "res",
                "dalvik",
                "freq",
                "idle",
                "binder_driver",
                "binder_lock",
            ]

        device_output_path = f"/data/local/tmp/trace_{int(time.time())}.perfetto-trace"

        # Build config commands
        # We'll use the simple command line arguments for perfetto instead of passing a full config file for now
        # to keep it simple and robust.

        cmd = [
            self.adb_path,
            "-s",
            device_serial,
            "shell",
            "perfetto",
            "-o",
            device_output_path,
            "-t",
            f"{duration_seconds}s",
            "-b",
            f"{buffer_size_kb}kb",
        ]

        # Append categories
        cmd.extend(categories)

        try:
            # 1. Start Capture
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
            # 2. Pull the file
            pull_cmd = [
                self.adb_path,
                "-s",
                device_serial,
                "pull",
                device_output_path,
                output_path,
            ]
            subprocess.run(
                pull_cmd,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
            # 3. Cleanup on device
            cleanup_cmd = [
                self.adb_path,
                "-s",
                device_serial,
                "shell",
                "rm",
                device_output_path,
            ]
            subprocess.run(
                cleanup_cmd,
                capture_output=True,
                check=False,
                **subprocess_hidden_window_kwargs(),
            )

            return output_path

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Perfetto capture failed: {e.stderr if e.stderr else e.stdout}"
            ) from e
