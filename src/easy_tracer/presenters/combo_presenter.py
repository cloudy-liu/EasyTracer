from typing import Dict, Any, Optional, Callable

from easy_tracer.models.requests import ComboRequest, PerfettoRequest, SimpleperfRequest, SystraceRequest, TraceviewStartRequest
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
        package_name = configs.get("package_name")
        output_dir = configs.get("output_dir")
        request = ComboRequest(
            device_serial=device_serial,
            duration_seconds=duration,
            output_dir=output_dir,
            systrace=(
                SystraceRequest(
                    device_serial=device_serial,
                    categories=configs.get("systrace_categories") or ["sched", "gfx", "view", "wm", "am"],
                    duration_seconds=duration,
                    buffer_size_kb=configs.get("systrace_buffer", 16384),
                    app_name=package_name,
                    output_dir=output_dir,
                ) if enabled_tools.get("systrace") else None
            ),
            perfetto=(
                PerfettoRequest(
                    device_serial=device_serial,
                    duration_seconds=duration,
                    buffer_size_kb=configs.get("perfetto_buffer", 32768),
                    categories=configs.get("perfetto_categories"),
                    preset=configs.get("perfetto_preset"),
                    output_dir=output_dir,
                ) if enabled_tools.get("perfetto") else None
            ),
            simpleperf=(
                SimpleperfRequest(
                    device_serial=device_serial,
                    app_name=package_name,
                    duration_seconds=duration,
                    frequency=configs.get("simpleperf_freq", 4000),
                    cold_start=configs.get("simpleperf_cold_start", False),
                    output_dir=output_dir,
                ) if enabled_tools.get("simpleperf") else None
            ),
            traceview=(
                TraceviewStartRequest(
                    device_serial=device_serial,
                    package_name=package_name,
                    sampling=configs.get("traceview_sampling", False),
                    interval=configs.get("traceview_interval", 1000),
                    output_dir=output_dir,
                ) if enabled_tools.get("traceview") and package_name else None
            ),
            auxiliary_options=configs.get("auxiliary_options") or {},
        )
        self.run_request(request)

    def run_request(self, request: ComboRequest):
        if not request.device_serial:
            self.error_message = "No device selected."
            self._notify_view()
            return

        if not any([request.systrace, request.perfetto, request.simpleperf, request.traceview]) and not any(request.auxiliary_options.values()):
            self.error_message = "Select at least one tool."
            self._notify_view()
            return

        self.is_running = True
        self.results = {}
        self.error_message = None
        self._notify_view()

        try:
            result = self.combo_service.run(request)
            self.results = result.files
            if result.errors:
                self.error_message = "; ".join(
                    f"{name}: {message}" for name, message in result.errors.items()
                )
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.is_running = False
            self._notify_view()
