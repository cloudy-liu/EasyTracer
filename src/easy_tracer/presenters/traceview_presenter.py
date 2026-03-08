from typing import Optional, Callable
from easy_tracer.models.requests import TraceviewStartRequest
from easy_tracer.services.traceview_service import TraceviewService

class TraceviewPresenter:
    def __init__(self, traceview_service: TraceviewService):
        self.traceview_service = traceview_service
        self.view_update: Optional[Callable[[], None]] = None

        # State
        self.is_tracing: bool = False
        self.current_package: Optional[str] = None
        self._active_request: Optional[TraceviewStartRequest] = None
        self._active_session = None
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
        request = TraceviewStartRequest(
            device_serial=device_serial,
            package_name=package_name,
            sampling=sampling,
            interval=interval,
        )
        self.start_request(request)

    def start_request(self, request: TraceviewStartRequest):
        if not request.device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        if not request.package_name:
            self.error_message = "Package name is required."
            self._notify_view()
            return

        self.error_message = None
        self.current_package = request.package_name

        try:
            self._active_request = request
            self._active_session = self.traceview_service.start_session(request)
            self.is_tracing = True
            self.last_output_path = None
        except Exception as e:
            self.error_message = f"Failed to start tracing: {str(e)}"
            self.is_tracing = False
            self._active_request = None
            self._active_session = None
        finally:
            self._notify_view()

    def stop_tracing(self, device_serial: str, output_dir: Optional[str] = None):
        if not device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        self.stop_capture(output_dir=output_dir)

    def stop_capture(self, output_dir: Optional[str] = None):
        if not self._active_session:
            self.error_message = "No active trace to stop."
            self.is_tracing = False
            self._notify_view()
            return

        try:
            result = self._active_session.stop(output_dir=output_dir)
            self.last_output_path = result.output_path
        except Exception as e:
            self.error_message = f"Failed to stop tracing: {str(e)}"
        finally:
            self.is_tracing = False
            self.current_package = None
            self._active_request = None
            self._active_session = None
            self._notify_view()
