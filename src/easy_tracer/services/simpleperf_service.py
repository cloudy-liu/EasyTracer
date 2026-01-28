import os
import time
from easy_tracer.framework.simpleperf_adapter import SimpleperfAdapter

class SimpleperfService:
    def __init__(self, simpleperf_adapter: SimpleperfAdapter, output_dir: str = "output"):
        self.simpleperf_adapter = simpleperf_adapter
        self.output_dir = output_dir

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def profile_app(
        self,
        device_serial: str,
        app_name: str,
        duration_seconds: int = 10,
        frequency: int = 4000,
        generate_report: bool = True,
        output_dir: str | None = None,
    ) -> str:
        """
        Profiles an Android app using simpleperf.
        Returns the path to the output (HTML report if generate_report is True, else perf.data).
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_dir = output_dir or self.output_dir
        session_dir = os.path.join(base_dir, f"simpleperf_{timestamp}")
        os.makedirs(session_dir, exist_ok=True)

        # Run profiler
        perf_data_path = self.simpleperf_adapter.run_app_profiler(
            device_serial=device_serial,
            app_name=app_name,
            output_dir=session_dir,
            duration_seconds=duration_seconds,
            frequency=frequency
        )

        if generate_report:
            html_path = os.path.join(session_dir, "report.html")
            return self.simpleperf_adapter.generate_html_report(perf_data_path, html_path)

        return perf_data_path

    def profile_system(
        self,
        device_serial: str,
        duration_seconds: int = 10,
        frequency: int = 4000,
        generate_report: bool = True,
        output_dir: str | None = None,
    ) -> str:
        """
        Performs system-wide profiling using simpleperf.
        Returns the path to the output.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_dir = output_dir or self.output_dir
        session_dir = os.path.join(base_dir, f"simpleperf_system_{timestamp}")
        os.makedirs(session_dir, exist_ok=True)

        perf_data_path = os.path.join(session_dir, "perf.data")

        self.simpleperf_adapter.run_simpleperf_record(
            device_serial=device_serial,
            output_path=perf_data_path,
            duration_seconds=duration_seconds,
            frequency=frequency
        )

        if generate_report:
            html_path = os.path.join(session_dir, "report.html")
            return self.simpleperf_adapter.generate_html_report(perf_data_path, html_path)

        return perf_data_path
