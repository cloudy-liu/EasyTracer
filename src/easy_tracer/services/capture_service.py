from __future__ import annotations

import logging
import os
import re
import time

from easy_tracer.framework import adb_helper as adb_helper_module
from easy_tracer.framework import systrace_adapter as systrace_adapter_module

logger = logging.getLogger(__name__)


class CaptureService:
    def __init__(
        self,
        systrace_adapter: systrace_adapter_module.SystraceAdapter,
        output_dir: str = "output",
        adb_helper: adb_helper_module.AdbHelper | None = None,
    ):
        self.systrace_adapter = systrace_adapter
        self.output_dir = output_dir
        self.adb_helper = adb_helper or adb_helper_module.AdbHelper()

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_available_categories(self, device_serial: str) -> list[str]:
        """Returns available systrace categories for the device."""
        return self.systrace_adapter.get_categories(device_serial)

    def get_ftrace_events(self, device_serial: str) -> list[str]:
        """Returns available ftrace events for the device."""
        return self.systrace_adapter.get_ftrace_events(device_serial)

    def start_capture(
        self,
        device_serial: str,
        categories: list[str],
        duration_seconds: int = 5,
        buffer_size_kb: int = 16384,
        app_name: str | None = None,
        output_dir: str | None = None,
    ) -> str:
        """
        Starts a systrace capture.
        Returns the path to the generated output file.
        """
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        model = self.systrace_adapter.get_device_model(device_serial) or device_serial
        sdk = self.systrace_adapter.get_device_sdk_version(device_serial)
        sdk_text = str(sdk) if sdk is not None else "unknown"
        filename = f"{self._sanitize_name(model)}_{sdk_text}_systrace_{timestamp}.html"
        base_dir = output_dir or self.output_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(base_dir, filename)

        # Ensure absolute path for the adapter
        output_path = os.path.abspath(output_path)

        self.systrace_adapter.run_systrace(
            output_file=output_path,
            time_seconds=duration_seconds,
            device_serial=device_serial,
            categories=categories,
            buffer_size_kb=buffer_size_kb,
            app_name=app_name,
        )

        return output_path

    @staticmethod
    def _sanitize_name(text: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", (text or "").strip())
        normalized = normalized.strip("_")
        return normalized or "unknown_device"

    def dump_auxiliary_logs(
        self,
        device_serial: str,
        output_prefix: str,
        options: dict[str, bool],
    ) -> dict[str, str]:
        """Dumps auxiliary logs based on selected options.

        Args:
            device_serial: Target device serial
            output_prefix: Base path for output files (without extension)
            options: Dict with keys 'logcat', 'packages', 'ps', 'meminfo'

        Returns:
            Dict mapping option name to output file path for successful dumps
        """
        results: dict[str, str] = {}

        dump_map = {
            "logcat": (self.adb_helper.dump_logcat, "_logcat.txt"),
            "packages": (self.adb_helper.dump_packages, "_packages.txt"),
            "ps": (self.adb_helper.dump_ps, "_ps.txt"),
            "meminfo": (self.adb_helper.dump_meminfo, "_meminfo.txt"),
        }

        for opt_name, (dump_fn, suffix) in dump_map.items():
            if not options.get(opt_name, False):
                continue
            try:
                output_path = output_prefix + suffix
                dump_fn(device_serial, output_path)
                results[opt_name] = output_path
                logger.info(f"Dumped {opt_name} to {output_path}")
            except Exception as e:
                logger.warning(f"Failed to dump {opt_name}: {e}")

        return results
