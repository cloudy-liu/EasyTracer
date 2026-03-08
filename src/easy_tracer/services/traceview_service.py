import os
import time
from dataclasses import dataclass
from typing import Optional
from easy_tracer.framework import traceview_adapter
from easy_tracer.models.requests import TraceviewStartRequest
from easy_tracer.models.results import CaptureResult


@dataclass
class TraceviewSession:
    service: "TraceviewService"
    request: TraceviewStartRequest

    def stop(self, output_dir: Optional[str] = None) -> CaptureResult:
        return self.service.stop_session(self.request, output_dir=output_dir)

class TraceviewService:
    def __init__(
        self,
        adapter: traceview_adapter.TraceviewAdapter,
        output_dir: str = "output",
    ):
        self.adapter = adapter
        self.output_dir = output_dir

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def start_tracing(self, device_serial: str, package_name: str, sampling: bool, interval: int):
        """Starts method tracing on the specified package."""
        request = TraceviewStartRequest(
            device_serial=device_serial,
            package_name=package_name,
            sampling=sampling,
            interval=interval,
        )
        self.start_session(request)

    def start_session(self, request: TraceviewStartRequest) -> TraceviewSession:
        self.adapter.start_tracing(
            request.device_serial,
            request.package_name,
            request.sampling,
            request.interval,
        )
        return TraceviewSession(service=self, request=request)

    def stop_tracing(
        self,
        device_serial: str,
        package_name: str,
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Stops method tracing and pulls the file.
        Returns the path to the pulled trace file.
        """
        request = TraceviewStartRequest(
            device_serial=device_serial,
            package_name=package_name,
            output_dir=output_dir,
        )
        return self.stop_session(request, output_dir=output_dir).output_path

    def stop_session(
        self,
        request: TraceviewStartRequest,
        output_dir: Optional[str] = None,
    ) -> CaptureResult:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"traceview_{request.package_name}_{timestamp}.trace"
        base_dir = output_dir or request.output_dir or self.output_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(base_dir, filename)

        # Ensure absolute path
        output_path = os.path.abspath(output_path)

        final_path = self.adapter.stop_tracing(
            request.device_serial,
            request.package_name,
            output_path,
        )
        return CaptureResult(
            tool="traceview",
            output_path=final_path,
            outputs={"trace": final_path},
        )
