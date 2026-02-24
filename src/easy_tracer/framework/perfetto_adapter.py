import time
from typing import List

from easy_tracer.framework import subprocess_utils


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

        # Use standard /data/misc/perfetto-traces/ which is writable by shell/traced
        # Avoids permission denied errors common in /data/local/tmp on newer Android versions
        device_output_path = f"/data/misc/perfetto-traces/trace_{int(time.time())}.perfetto-trace"

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

        # 1. Start Capture
        subprocess_utils.check_output(cmd)

        # 2. Pull the file
        pull_cmd = [
            self.adb_path,
            "-s",
            device_serial,
            "pull",
            device_output_path,
            output_path,
        ]
        subprocess_utils.check_output(pull_cmd)

        # 3. Cleanup on device (best-effort)
        cleanup_cmd = [
            self.adb_path,
            "-s",
            device_serial,
            "shell",
            "rm",
            device_output_path,
        ]
        try:
            subprocess_utils.check_output(cleanup_cmd)
        except RuntimeError:
            pass

        return output_path
