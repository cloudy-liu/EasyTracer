import threading
import os
from typing import Dict, Any
from easy_tracer.models.requests import ComboRequest, PerfettoRequest, SimpleperfRequest, SystraceRequest, TraceviewStartRequest
from easy_tracer.models.results import ComboResult
from easy_tracer.services.capture_service import CaptureService
from easy_tracer.services.simpleperf_service import SimpleperfService
from easy_tracer.services.perfetto_service import PerfettoService
from easy_tracer.services.traceview_service import TraceviewService

class ComboService:
    def __init__(
        self,
        systrace_service: CaptureService,
        simpleperf_service: SimpleperfService,
        perfetto_service: PerfettoService,
        traceview_service: TraceviewService,
        output_dir: str = "output"
    ):
        self.systrace = systrace_service
        self.simpleperf = simpleperf_service
        self.perfetto = perfetto_service
        self.traceview = traceview_service
        self.output_dir = output_dir

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def start_combo_capture(
        self,
        device_serial: str,
        duration: int,
        enabled_tools: Dict[str, bool],
        configs: Dict[str, Any]
    ) -> Dict[str, str]:
        package_name = configs.get('package_name')
        output_dir = configs.get('output_dir')
        results: dict[str, str] = {}
        errors: dict[str, str] = {}
        threads: list[threading.Thread] = []
        traceview_started = False

        def run_tool(name: str, fn) -> None:
            try:
                results[name] = fn()
            except Exception as exc:
                errors[name] = str(exc)

        if enabled_tools.get('traceview') and package_name:
            try:
                self.traceview.start_tracing(
                    device_serial=device_serial,
                    package_name=package_name,
                    sampling=configs.get('traceview_sampling', False),
                    interval=configs.get('traceview_interval', 1000),
                )
                traceview_started = True
            except Exception as exc:
                errors['traceview'] = str(exc)

        if enabled_tools.get('systrace'):
            thread = threading.Thread(
                target=run_tool,
                args=(
                    'systrace',
                    lambda: self.systrace.start_capture(
                        device_serial=device_serial,
                        categories=configs.get('systrace_categories') or ["sched", "gfx", "view", "wm", "am"],
                        duration_seconds=duration,
                        buffer_size_kb=configs.get('systrace_buffer', 16384),
                        app_name=package_name,
                        output_dir=output_dir,
                    ),
                ),
            )
            thread.start()
            threads.append(thread)

        if enabled_tools.get('perfetto'):
            thread = threading.Thread(
                target=run_tool,
                args=(
                    'perfetto',
                    lambda: self.perfetto.record_trace(
                        device_serial=device_serial,
                        duration_seconds=duration,
                        buffer_size_kb=configs.get('perfetto_buffer', 32768),
                        categories=configs.get('perfetto_categories'),
                        output_dir=output_dir,
                        preset=configs.get('perfetto_preset'),
                        config=configs.get('perfetto_config'),
                    ),
                ),
            )
            thread.start()
            threads.append(thread)

        if enabled_tools.get('simpleperf'):
            if package_name:
                target = lambda: self.simpleperf.profile_app(
                    device_serial=device_serial,
                    app_name=package_name,
                    duration_seconds=duration,
                    frequency=configs.get('simpleperf_freq', 4000),
                    output_dir=output_dir,
                    cold_start=configs.get('simpleperf_cold_start', False),
                )
            else:
                target = lambda: self.simpleperf.profile_system(
                    device_serial=device_serial,
                    duration_seconds=duration,
                    frequency=configs.get('simpleperf_freq', 4000),
                    output_dir=output_dir,
                )

            thread = threading.Thread(target=run_tool, args=('simpleperf', target))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        if traceview_started and 'traceview' not in errors:
            try:
                results['traceview'] = self.traceview.stop_tracing(
                    device_serial=device_serial,
                    package_name=package_name,
                    output_dir=output_dir,
                )
            except Exception as exc:
                errors['traceview'] = str(exc)

        if errors:
            error_msg = "; ".join([f"{k}: {v}" for k, v in errors.items()])
            raise RuntimeError(f"Combo capture errors: {error_msg}")
        return results

    def run(self, request: ComboRequest) -> ComboResult:
        """Run combo capture and preserve partial successes."""
        files: dict[str, str] = {}
        errors: dict[str, str] = {}
        auxiliary_outputs: dict[str, str] = {}
        threads: list[threading.Thread] = []
        traceview_session = None

        def run_tool(name: str, fn) -> None:
            try:
                result = fn()
                files[name] = result.output_path
            except Exception as exc:
                errors[name] = str(exc)

        if request.traceview:
            try:
                traceview_session = self.traceview.start_session(request.traceview)
            except Exception as exc:
                errors['traceview'] = str(exc)

        if request.systrace:
            thread = threading.Thread(target=run_tool, args=('systrace', lambda: self.systrace.run(request.systrace)))
            thread.start()
            threads.append(thread)

        if request.perfetto:
            thread = threading.Thread(target=run_tool, args=('perfetto', lambda: self.perfetto.run(request.perfetto)))
            thread.start()
            threads.append(thread)

        if request.simpleperf:
            thread = threading.Thread(target=run_tool, args=('simpleperf', lambda: self.simpleperf.run(request.simpleperf)))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        if traceview_session is not None and 'traceview' not in errors:
            try:
                traceview_result = traceview_session.stop(output_dir=request.output_dir)
                files['traceview'] = traceview_result.output_path
            except Exception as exc:
                errors['traceview'] = str(exc)

        if request.auxiliary_options:
            try:
                prefix = os.path.join(request.output_dir or self.output_dir, 'aux')
                auxiliary_outputs = self.systrace.dump_auxiliary_logs(
                    device_serial=request.device_serial,
                    output_prefix=prefix,
                    options=request.auxiliary_options,
                )
                files.update(auxiliary_outputs)
            except Exception as exc:
                errors['auxiliary'] = str(exc)

        if errors and files:
            status = 'partial'
        elif errors:
            status = 'error'
        else:
            status = 'success'

        return ComboResult(
            status=status,
            files=files,
            errors=errors,
            auxiliary_outputs=auxiliary_outputs,
        )
