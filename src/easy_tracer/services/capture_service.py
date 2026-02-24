import os
import time
import re
from typing import List, Optional
from easy_tracer.framework import systrace_adapter


class CaptureService:
    def __init__(
        self,
        systrace_adapter: systrace_adapter.SystraceAdapter,
        output_dir: str = "output",
    ):
        self.systrace_adapter = systrace_adapter
        self.output_dir = output_dir

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_available_categories(self, device_serial: str) -> List[str]:
        """Returns available systrace categories for the device."""
        return self.systrace_adapter.get_categories(device_serial)

    def get_ftrace_events(self, device_serial: str) -> List[str]:
        """Returns available ftrace events for the device."""
        return self.systrace_adapter.get_ftrace_events(device_serial)

    def start_capture(
        self,
        device_serial: str,
        categories: List[str],
        duration_seconds: int = 5,
        buffer_size_kb: int = 16384,
        app_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        create_subfolder: bool = False,
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
        if create_subfolder:
            base_dir = os.path.join(base_dir, f"systrace_{timestamp}")
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
