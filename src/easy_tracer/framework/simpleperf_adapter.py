"""Simpleperf CPU profiling adapter.

Delegates all ADB operations to adb_helper for unified resource management.
"""

from __future__ import annotations

import concurrent.futures  # noqa: F401 - Required for PyInstaller bundling
import webbrowser  # noqa: F401 - Required for PyInstaller bundling
import contextlib
import importlib.util
import io
import logging
import os
import sys
import time

from easy_tracer.framework import adb_helper

logger = logging.getLogger(__name__)


class SimpleperfAdapter:
    def __init__(
        self,
        adb: adb_helper.AdbHelper | None = None,
        adb_path: str = "adb",
    ):
        self.adb = adb if adb else adb_helper.AdbHelper(adb_path)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.simpleperf_dir = os.path.join(current_dir, "external", "simpleperf")
        self.report_html_path = os.path.join(self.simpleperf_dir, "report_html.py")

    def _force_stop_app(self, device_serial: str, app_name: str) -> None:
        """Force stop an app for cold start."""
        logger.info(f"Force stopping {app_name}...")
        try:
            self.adb.run_shell(device_serial, "am", "force-stop", app_name)
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Failed to force stop {app_name}: {e}")

    def _import_and_run_script(self, script_path: str, module_name: str, args: list) -> str:
        """Helper to import a script and run its main function with patched sys.argv"""
        if self.simpleperf_dir not in sys.path:
            sys.path.insert(0, self.simpleperf_dir)

        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load {module_name} from {script_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        original_argv = sys.argv
        sys.argv = [os.path.basename(script_path)] + args

        output_capture = io.StringIO()
        try:
            with contextlib.redirect_stdout(output_capture), contextlib.redirect_stderr(output_capture):
                try:
                    module.main()
                except SystemExit as e:
                    if e.code != 0:
                        raise RuntimeError(f"{module_name} exited with code {e.code}")
        except Exception as e:
            captured = output_capture.getvalue()
            raise RuntimeError(f"{module_name} failed: {str(e)}\nLog: {captured}")
        finally:
            sys.argv = original_argv

        return output_capture.getvalue()

    def run_app_profiler(
        self,
        device_serial: str,
        app_name: str,
        output_dir: str,
        duration_seconds: int = 10,
        frequency: int = 4000,
        record_options: str | None = None,
        cold_start: bool = False,
    ) -> str:
        """Profiles an Android app using simpleperf."""
        app_profiler_path = os.path.join(self.simpleperf_dir, "app_profiler.py")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        perf_data_path = os.path.join(output_dir, f"perf_{timestamp}.data")

        if cold_start:
            self._force_stop_app(device_serial, app_name)

        if not os.path.exists(app_profiler_path):
            self.run_simpleperf_record(
                device_serial=device_serial,
                output_path=perf_data_path,
                duration_seconds=duration_seconds,
                frequency=frequency,
                process_name=app_name,
            )
            return perf_data_path

        original_cwd = os.getcwd()
        os.chdir(output_dir)

        try:
            args = [
                "-p", app_name,
                "-o", perf_data_path,
                "--serial", device_serial,
                "-r", f"-f {frequency} --duration {duration_seconds}",
            ]

            if record_options:
                args[-1] = record_options

            self._import_and_run_script(app_profiler_path, "app_profiler", args)
            return perf_data_path
        finally:
            os.chdir(original_cwd)

    def generate_html_report(self, perf_data_path: str, output_html_path: str) -> str:
        """Generates an HTML report from perf.data."""
        if not os.path.exists(self.report_html_path):
            raise FileNotFoundError(f"report_html.py not found at {self.report_html_path}")

        if not os.path.exists(perf_data_path):
            raise FileNotFoundError(f"perf.data not found at {perf_data_path}")

        args = ["-i", perf_data_path, "-o", output_html_path]
        self._import_and_run_script(self.report_html_path, "report_html", args)
        return output_html_path

    def run_simpleperf_record(
        self,
        device_serial: str,
        output_path: str,
        duration_seconds: int = 10,
        frequency: int = 4000,
        pid: int | None = None,
        process_name: str | None = None,
    ) -> str:
        """Runs simpleperf record directly on the device."""
        device_perf_path = "/data/local/tmp/perf.data"

        cmd_parts = ["simpleperf", "record", "-f", str(frequency), "--duration", str(duration_seconds)]

        if pid:
            cmd_parts.extend(["-p", str(pid)])
        elif process_name:
            cmd_parts.extend(["--app", process_name])
        else:
            cmd_parts.append("-a")  # System-wide

        cmd_parts.extend(["-o", device_perf_path])

        self.adb.run_shell(device_serial, *cmd_parts)
        self.adb.pull_file(device_serial, device_perf_path, output_path)

        return output_path
