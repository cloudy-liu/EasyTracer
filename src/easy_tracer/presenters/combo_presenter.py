from typing import Dict, Any, Optional, Callable
from easy_tracer.services.combo_service import ComboService

class ComboPresenter:
    def __init__(self, combo_service: ComboService):
        self.combo_service = combo_service
        self.view_update: Optional[Callable[[], None]] = None

        # State
        self.is_running: bool = False
        self.results: Dict[str, str] = {}
        self.error_message: Optional[str] = None

    def bind_view_update(self, callback: Callable[[], None]):
        self.view_update = callback

    def _notify_view(self):
        if self.view_update:
            self.view_update()

    def start_combo(
        self,
        device_serial: str,
        duration: int,
        enabled_tools: Dict[str, bool],
        configs: Dict[str, Any]
    ):
        if not device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        if not any(enabled_tools.values()):
            self.error_message = "Select at least one tool."
            self._notify_view()
            return

        self.is_running = True
        self.results = {}
        self.error_message = None
        self._notify_view()

        try:
            self.results = self.combo_service.start_combo_capture(
                device_serial=device_serial,
                duration=duration,
                enabled_tools=enabled_tools,
                configs=configs
            )
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.is_running = False
            self._notify_view()
