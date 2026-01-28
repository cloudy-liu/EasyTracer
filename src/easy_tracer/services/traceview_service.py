import os
import time
from easy_tracer.framework.traceview_adapter import TraceviewAdapter

class TraceviewService:
    def __init__(self, adapter: TraceviewAdapter, output_dir: str = "output"):
        self.adapter = adapter
        self.output_dir = output_dir

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def start_tracing(self, device_serial: str, package_name: str, sampling: bool, interval: int):
        """Starts method tracing on the specified package."""
        self.adapter.start_tracing(device_serial, package_name, sampling, interval)

    def stop_tracing(
        self,
        device_serial: str,
        package_name: str,
        output_dir: str | None = None,
        create_subfolder: bool = False,
    ) -> str:
        """
        Stops method tracing and pulls the file.
        Returns the path to the pulled trace file.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"traceview_{package_name}_{timestamp}.trace"
        base_dir = output_dir or self.output_dir
        if create_subfolder:
            base_dir = os.path.join(base_dir, f"traceview_{timestamp}")
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(base_dir, filename)

        # Ensure absolute path
        output_path = os.path.abspath(output_path)

        return self.adapter.stop_tracing(device_serial, package_name, output_path)
