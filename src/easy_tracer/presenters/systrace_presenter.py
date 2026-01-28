from typing import List, Optional, Callable
from easy_tracer.services.capture_service import CaptureService

class SystracePresenter:
    def __init__(self, capture_service: CaptureService):
        self.capture_service = capture_service
        self.view_update: Optional[Callable[[], None]] = None

        # State
        self.categories: List[str] = []
        self.ftrace_events: List[str] = []
        self.is_loading_categories: bool = False
        self.is_loading_ftrace: bool = False
        self.is_capturing: bool = False
        self.last_output_path: Optional[str] = None
        self.error_message: Optional[str] = None

    def bind_view_update(self, callback: Callable[[], None]):
        self.view_update = callback

    def _notify_view(self):
        if self.view_update:
            self.view_update()

    def load_categories(self, device_serial: str):
        """Loads categories for the specific device."""
        if not device_serial:
            return

        self.is_loading_categories = True
        self.categories = []
        self.error_message = None
        self._notify_view()

        try:
            self.categories = self.capture_service.get_available_categories(device_serial)
        except Exception as e:
            self.error_message = f"Failed to load categories: {str(e)}"
        finally:
            self.is_loading_categories = False
            self._notify_view()

    def load_ftrace_events(self, device_serial: str):
        """Loads ftrace events for the specific device."""
        if not device_serial:
            return

        self.is_loading_ftrace = True
        self.ftrace_events = []
        self.error_message = None
        self._notify_view()

        try:
            self.ftrace_events = self.capture_service.get_ftrace_events(device_serial)
        except Exception as e:
            self.error_message = f"Failed to load ftrace events: {str(e)}"
        finally:
            self.is_loading_ftrace = False
            self._notify_view()

    def start_capture(
        self,
        device_serial: str,
        selected_categories: List[str],
        duration: int,
        buffer_size: int,
        app_name: Optional[str],
        output_dir: Optional[str] = None,
        create_subfolder: bool = False,
    ):
        if not device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        if not selected_categories:
            self.error_message = "No categories selected."
            self._notify_view()
            return

        self.is_capturing = True
        self.last_output_path = None
        self.error_message = None
        self._notify_view()

        try:
            path = self.capture_service.start_capture(
                device_serial=device_serial,
                categories=selected_categories,
                duration_seconds=duration,
                buffer_size_kb=buffer_size,
                app_name=app_name,
                output_dir=output_dir,
                create_subfolder=create_subfolder,
            )
            self.last_output_path = path
        except Exception as e:
            self.error_message = f"Capture failed: {str(e)}"
        finally:
            self.is_capturing = False
            self._notify_view()
