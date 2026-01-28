import os
import sys
import io
import contextlib
import importlib.util
import subprocess
from typing import Optional
from easy_tracer.framework.subprocess_utils import subprocess_hidden_window_kwargs


class SimpleperfAdapter:
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path
        # Calculate path to simpleperf scripts
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.simpleperf_dir = os.path.join(current_dir, "external", "simpleperf")
        self.app_profiler_path = os.path.join(self.simpleperf_dir, "app_profiler.py")
        self.report_html_path = os.path.join(self.simpleperf_dir, "report_html.py")

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

        # Patch sys.argv
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
        record_options: Optional[str] = None,
    ) -> str:
        """Runs app_profiler.py to profile an Android app."""
        if not os.path.exists(self.app_profiler_path):
            raise FileNotFoundError(
                f"app_profiler.py not found at {self.app_profiler_path}"
            )

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        perf_data_path = os.path.join(output_dir, "perf.data")

        # Change CWD to output_dir so relative paths work if script uses them
        # app_profiler writes to CWD usually or uses -o
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
                args[-1] = record_options # Replace the -r default

            self._import_and_run_script(self.app_profiler_path, "app_profiler", args)
            return perf_data_path
        finally:
            os.chdir(original_cwd)

    def generate_html_report(self, perf_data_path: str, output_html_path: str) -> str:
        """Generates an HTML report from perf.data."""
        if not os.path.exists(self.report_html_path):
            raise FileNotFoundError(
                f"report_html.py not found at {self.report_html_path}"
            )

        if not os.path.exists(perf_data_path):
            raise FileNotFoundError(f"perf.data not found at {perf_data_path}")

        args = [
            "-i", perf_data_path,
            "-o", output_html_path,
        ]

        self._import_and_run_script(self.report_html_path, "report_html", args)
        return output_html_path

    def run_simpleperf_record(
        self,
        device_serial: str,
        output_path: str,
        duration_seconds: int = 10,
        frequency: int = 4000,
        pid: Optional[int] = None,
        process_name: Optional[str] = None,
    ) -> str:
        """Runs simpleperf record directly on the device."""
        simpleperf_cmd = (
            f"simpleperf record -f {frequency} --duration {duration_seconds}"
        )

        if pid:
            simpleperf_cmd += f" -p {pid}"
        elif process_name:
            simpleperf_cmd += f" --app {process_name}"
        else:
            simpleperf_cmd += " -a"  # System-wide

        simpleperf_cmd += " -o /data/local/tmp/perf.data"
        adb_cmd = [self.adb_path, "-s", device_serial, "shell", simpleperf_cmd]

        try:
            subprocess.run(
                adb_cmd,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
            # Pull the file
            pull_cmd = [
                self.adb_path,
                "-s",
                device_serial,
                "pull",
                "/data/local/tmp/perf.data",
                output_path,
            ]
            subprocess.run(
                pull_cmd,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )

            return output_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Simpleperf record failed: {e.stderr}") from e
