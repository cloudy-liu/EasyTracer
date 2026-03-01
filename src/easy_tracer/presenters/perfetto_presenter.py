from typing import List, Optional, Callable, Dict
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
        if not device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        self.is_recording = True
        self.last_output_path = None
        self.auxiliary_outputs = {}
        self.error_message = None
        self._notify_view()

        try:
            path = self.perfetto_service.record_trace(
                device_serial=device_serial,
                duration_seconds=duration,
                buffer_size_kb=buffer_size,
                categories=categories if not preset and not config else None,
                output_dir=output_dir,
                preset=preset,
                config=config,
            )
            self.last_output_path = path

            # Dump auxiliary logs if requested and capture_service available
            if auxiliary_options and any(auxiliary_options.values()) and self.capture_service:
                prefix = path.rsplit(".", 1)[0] if "." in path else path
                self.auxiliary_outputs = self.capture_service.dump_auxiliary_logs(
                    device_serial=device_serial,
                    output_prefix=prefix,
                    options=auxiliary_options,
                )
        except Exception as e:
            self.error_message = f"Perfetto recording failed: {str(e)}"
        finally:
            self.is_recording = False
            self._notify_view()
