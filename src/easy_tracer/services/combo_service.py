import threading
import os
from typing import Dict, Any
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
        """
        Runs selected tools in parallel.
        Returns a dictionary of tool name -> output file path.
        """
        results = {}
        errors = {}
        threads = []

        package_name = configs.get('package_name')

        # --- 1. Start Non-Blocking / Init ---

        # Traceview start (if enabled and package provided)
        if enabled_tools.get('traceview'):
            if not package_name:
                errors['traceview'] = "Package name required for Traceview"
            else:
                try:
                    self.traceview.start_tracing(
                        device_serial,
                        package_name,
                        configs.get('traceview_sampling', False),
                        configs.get('traceview_interval', 1000)
                    )
                except Exception as e:
                    errors['traceview'] = str(e)

        # --- 2. Define Worker Functions for Blocking Tools ---

        def run_systrace():
            try:
                # Default categories if not provided
                cats = configs.get('systrace_categories') or ["sched", "gfx", "view", "wm", "am"]
                path = self.systrace.start_capture(
                    device_serial,
                    categories=cats,
                    duration_seconds=duration,
                    buffer_size_kb=configs.get('systrace_buffer', 16384),
                    app_name=package_name
                )
                results['systrace'] = path
            except Exception as e:
                errors['systrace'] = str(e)

        def run_perfetto():
            try:
                path = self.perfetto.record_trace(
                    device_serial,
                    duration_seconds=duration,
                    buffer_size_kb=configs.get('perfetto_buffer', 32768),
                    categories=configs.get('perfetto_categories')
                )
                results['perfetto'] = path
            except Exception as e:
                errors['perfetto'] = str(e)

        def run_simpleperf():
            try:
                if package_name:
                    path = self.simpleperf.profile_app(
                        device_serial,
                        package_name,
                        duration_seconds=duration,
                        frequency=configs.get('simpleperf_freq', 4000)
                    )
                else:
                    path = self.simpleperf.profile_system(
                        device_serial,
                        duration_seconds=duration,
                        frequency=configs.get('simpleperf_freq', 4000)
                    )
                results['simpleperf'] = path
            except Exception as e:
                errors['simpleperf'] = str(e)

        # --- 3. Start Threads ---

        if enabled_tools.get('systrace'):
            t = threading.Thread(target=run_systrace)
            t.start()
            threads.append(t)

        if enabled_tools.get('perfetto'):
            t = threading.Thread(target=run_perfetto)
            t.start()
            threads.append(t)

        if enabled_tools.get('simpleperf'):
            t = threading.Thread(target=run_simpleperf)
            t.start()
            threads.append(t)

        # --- 4. Wait for Blocking Tools ---
        for t in threads:
            t.join()

        # --- 5. Stop Traceview ---
        if enabled_tools.get('traceview') and 'traceview' not in errors:
            try:
                # We stop traceview after the duration (blocking tools finished)
                path = self.traceview.stop_tracing(device_serial, package_name)
                results['traceview'] = path
            except Exception as e:
                errors['traceview'] = str(e)

        if errors:
            # We return partial results but raise an error with details
            error_msg = "; ".join([f"{k}: {v}" for k, v in errors.items()])
            # If we have at least one success, we might want to return it,
            # but usually an exception is better to notify UI.
            # Let's attach results to the exception or just return what we have and let presenter handle errors?
            # For simplicity, let's return results and put errors in a special key or raise if critical.
            # Raising Runtime Error is easiest for now.
            raise RuntimeError(f"Combo capture errors: {error_msg}")

        return results
