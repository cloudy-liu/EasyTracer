import os
import time
from typing import List
from easy_tracer.framework.perfetto_adapter import PerfettoAdapter

class PerfettoService:
    def __init__(self, perfetto_adapter: PerfettoAdapter, output_dir: str = "output"):
        self.perfetto_adapter = perfetto_adapter
        self.output_dir = output_dir

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def record_trace(
        self,
        device_serial: str,
        duration_seconds: int = 10,
        buffer_size_kb: int = 32768,
        categories: List[str] = None,
        output_dir: str | None = None,
        create_subfolder: bool = False,
    ) -> str:
        """
        Records a Perfetto trace.
        Returns the path to the output file.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"perfetto_{timestamp}.perfetto-trace"
        base_dir = output_dir or self.output_dir
        if create_subfolder:
            base_dir = os.path.join(base_dir, f"perfetto_{timestamp}")
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(base_dir, filename)

        # Ensure absolute path
        output_path = os.path.abspath(output_path)

        self.perfetto_adapter.record_trace(
            device_serial=device_serial,
            output_path=output_path,
            duration_seconds=duration_seconds,
            buffer_size_kb=buffer_size_kb,
            categories=categories
        )

        return output_path
