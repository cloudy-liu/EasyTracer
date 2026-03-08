from typing import List, Optional, Callable, Dict
from easy_tracer.models.requests import PerfettoRequest
from easy_tracer.services.perfetto_service import PerfettoService
from easy_tracer.services.capture_service import CaptureService
from easy_tracer.framework.perfetto_config_builder import PerfettoConfig

class PerfettoPresenter:
    def __init__(
        self,
        perfetto_service: PerfettoService,
        capture_service: Optional[CaptureService] = None,
    ):
        self.perfetto_service = perfetto_service
        self.capture_service = capture_service
        self.view_update: Optional[Callable[[], None]] = None

        # State
        self.is_recording: bool = False
        self.last_output_path: Optional[str] = None
        self.auxiliary_outputs: Dict[str, str] = {}
        self.error_message: Optional[str] = None

    def bind_view_update(self, callback: Callable[[], None]):
        self.view_update = callback

    def _notify_view(self):
        if self.view_update:
            self.view_update()

    def start_recording(
        self,
        device_serial: str,
        duration: int,
        buffer_size: int,
        categories: List[str],
        output_dir: Optional[str] = None,
        auxiliary_options: Optional[Dict[str, bool]] = None,
        preset: Optional[str] = None,
        config: Optional[PerfettoConfig] = None,
    ):
        request = PerfettoRequest(
            device_serial=device_serial,
            duration_seconds=duration,
            buffer_size_kb=buffer_size,
            categories=categories,
            output_dir=output_dir,
            preset=preset,
            config=config,
            auxiliary_options=auxiliary_options or {},
        )
        self.run_request(request)

    def run_request(self, request: PerfettoRequest):
        if not request.device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        self.is_recording = True
        self.last_output_path = None
        self.auxiliary_outputs = {}
        self.error_message = None
        self._notify_view()

        try:
            result = self.perfetto_service.run(request)
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
            self.error_message = f"Perfetto recording failed: {str(e)}"
        finally:
            self.is_recording = False
            self._notify_view()
