from typing import Optional, Callable
from easy_tracer.services.traceview_service import TraceviewService

class TraceviewPresenter:
    def __init__(self, traceview_service: TraceviewService):
        self.traceview_service = traceview_service
        self.view_update: Optional[Callable[[], None]] = None

        # State
        self.is_tracing: bool = False
        self.current_package: Optional[str] = None
        self.last_output_path: Optional[str] = None
        self.error_message: Optional[str] = None

    def bind_view_update(self, callback: Callable[[], None]):
        self.view_update = callback

    def _notify_view(self):
        if self.view_update:
            self.view_update()

    def start_tracing(
        self,
        device_serial: str,
        package_name: str,
        sampling: bool,
        interval: int
    ):
        if not device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        if not package_name:
            self.error_message = "Package name is required."
            self._notify_view()
            return

        self.error_message = None
        self.current_package = package_name

        try:
            self.traceview_service.start_tracing(
                device_serial=device_serial,
                package_name=package_name,
                sampling=sampling,
                interval=interval
            )
            self.is_tracing = True
            self.last_output_path = None
        except Exception as e:
            self.error_message = f"Failed to start tracing: {str(e)}"
            self.is_tracing = False
        finally:
            self._notify_view()

    def stop_tracing(self, device_serial: str, output_dir: Optional[str] = None, create_subfolder: bool = False):
        if not device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        if not self.current_package:
             # Should not happen if state is consistent
            self.error_message = "No active trace to stop."
            self.is_tracing = False
            self._notify_view()
            return

        try:
            path = self.traceview_service.stop_tracing(
                device_serial=device_serial,
                package_name=self.current_package,
                output_dir=output_dir,
                create_subfolder=create_subfolder,
            )
            self.last_output_path = path
        except Exception as e:
             self.error_message = f"Failed to stop tracing: {str(e)}"
        finally:
            self.is_tracing = False
            self.current_package = None
            self._notify_view()
