import os
import time
from typing import Optional
from easy_tracer.framework import simpleperf_adapter
from easy_tracer.models.requests import SimpleperfRequest
from easy_tracer.models.results import CaptureResult

class SimpleperfService:
    def __init__(
        self,
        simpleperf_adapter: simpleperf_adapter.SimpleperfAdapter,
        output_dir: str = "output",
    ):
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
        output_dir: Optional[str] = None,
        cold_start: bool = False,
    ) -> str:
        """
        Profiles an Android app using simpleperf.
        Returns the path to the output (HTML report if generate_report is True, else perf.data).
        """
        request = SimpleperfRequest(
            device_serial=device_serial,
            app_name=app_name,
            duration_seconds=duration_seconds,
            frequency=frequency,
            output_dir=output_dir,
            cold_start=cold_start,
            generate_report=generate_report,
        )
        return self.run(request).output_path

    def run(self, request: SimpleperfRequest) -> CaptureResult:
        """Run simpleperf using a shared request contract."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_dir = request.output_dir or self.output_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)

        if request.app_name:
            perf_data_path = self.simpleperf_adapter.run_app_profiler(
                device_serial=request.device_serial,
                app_name=request.app_name,
                output_dir=base_dir,
                duration_seconds=request.duration_seconds,
                frequency=request.frequency,
                cold_start=request.cold_start,
            )
        else:
            perf_data_path = os.path.join(base_dir, f"perf_{timestamp}.data")
            self.simpleperf_adapter.run_simpleperf_record(
                device_serial=request.device_serial,
                output_path=perf_data_path,
                duration_seconds=request.duration_seconds,
                frequency=request.frequency,
            )

        if request.generate_report:
            html_path = os.path.join(base_dir, f"report_{timestamp}.html")
            output_path = self.simpleperf_adapter.generate_html_report(perf_data_path, html_path)
        else:
            output_path = perf_data_path

        return CaptureResult(
            tool="simpleperf",
            output_path=output_path,
            outputs={
                "report": output_path if request.generate_report else "",
                "perf_data": perf_data_path,
            },
        )

    def profile_system(
        self,
        device_serial: str,
        duration_seconds: int = 10,
        frequency: int = 4000,
        generate_report: bool = True,
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Performs system-wide profiling using simpleperf.
        Returns the path to the output.
        """
        request = SimpleperfRequest(
            device_serial=device_serial,
            duration_seconds=duration_seconds,
            frequency=frequency,
            output_dir=output_dir,
            generate_report=generate_report,
        )
        return self.run(request).output_path
