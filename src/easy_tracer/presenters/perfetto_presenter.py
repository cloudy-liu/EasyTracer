from typing import List, Optional, Callable
from easy_tracer.services.perfetto_service import PerfettoService

class PerfettoPresenter:
    def __init__(self, perfetto_service: PerfettoService):
        self.perfetto_service = perfetto_service
        self.view_update: Optional[Callable[[], None]] = None

        # State
        self.is_recording: bool = False
        self.last_output_path: Optional[str] = None
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
        create_subfolder: bool = False,
    ):
        if not device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        self.is_recording = True
        self.last_output_path = None
        self.error_message = None
        self._notify_view()

        try:
            path = self.perfetto_service.record_trace(
                device_serial=device_serial,
                duration_seconds=duration,
                buffer_size_kb=buffer_size,
                categories=categories,
                output_dir=output_dir,
                create_subfolder=create_subfolder,
            )
            self.last_output_path = path
        except Exception as e:
            self.error_message = f"Perfetto recording failed: {str(e)}"
        finally:
            self.is_recording = False
            self._notify_view()
