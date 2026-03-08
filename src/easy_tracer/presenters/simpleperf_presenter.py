from typing import Optional, Callable, Dict
from easy_tracer.models.requests import SimpleperfRequest
from easy_tracer.services.simpleperf_service import SimpleperfService
from easy_tracer.services.capture_service import CaptureService

class SimpleperfPresenter:
    def __init__(
        self,
        simpleperf_service: SimpleperfService,
        capture_service: Optional[CaptureService] = None,
    ):
        self.simpleperf_service = simpleperf_service
        self.capture_service = capture_service
        self.view_update: Optional[Callable[[], None]] = None

        # State
        self.is_profiling: bool = False
        self.last_output_path: Optional[str] = None
        self.auxiliary_outputs: Dict[str, str] = {}
        self.error_message: Optional[str] = None

    def bind_view_update(self, callback: Callable[[], None]):
        self.view_update = callback

    def _notify_view(self):
        if self.view_update:
            self.view_update()

    def start_app_profiling(
        self,
        device_serial: str,
        app_name: str,
        duration: int,
        frequency: int,
        output_dir: Optional[str] = None,
        cold_start: bool = False,
        auxiliary_options: Optional[Dict[str, bool]] = None,
    ):
        request = SimpleperfRequest(
            device_serial=device_serial,
            app_name=app_name,
            duration_seconds=duration,
            frequency=frequency,
            output_dir=output_dir,
            cold_start=cold_start,
            auxiliary_options=auxiliary_options or {},
        )
        self.run_request(request)

    def start_system_profiling(
        self,
        device_serial: str,
        duration: int,
        frequency: int,
        output_dir: Optional[str] = None,
        auxiliary_options: Optional[Dict[str, bool]] = None,
    ):
        request = SimpleperfRequest(
            device_serial=device_serial,
            duration_seconds=duration,
            frequency=frequency,
            output_dir=output_dir,
            auxiliary_options=auxiliary_options or {},
        )
        self.run_request(request)

    def run_request(self, request: SimpleperfRequest):
        if not request.device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        if request.app_name == "":
            self.error_message = "App name is required for app profiling."
            self._notify_view()
            return

        self.is_profiling = True
        self.last_output_path = None
        self.auxiliary_outputs = {}
        self.error_message = None
        self._notify_view()

        try:
            result = self.simpleperf_service.run(request)
            self.last_output_path = result.output_path
            self.auxiliary_outputs = result.auxiliary_outputs

            # Dump auxiliary logs if requested and capture_service available
            if request.auxiliary_options and any(request.auxiliary_options.values()) and self.capture_service:
                prefix = result.output_path.rsplit(".", 1)[0] if "." in result.output_path else result.output_path
                self.auxiliary_outputs = self.capture_service.dump_auxiliary_logs(
                    device_serial=request.device_serial,
                    output_prefix=prefix,
                    options=request.auxiliary_options,
                )
        except Exception as e:
            task_name = "App" if request.app_name else "System"
            self.error_message = f"{task_name} profiling failed: {str(e)}"
        finally:
            self.is_profiling = False
            self._notify_view()
