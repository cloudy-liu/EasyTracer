import os
import sys
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

        cmd = [
            sys.executable,
            self.app_profiler_path,
            "-p",
            app_name,
            "-o",
            perf_data_path,
            "--serial",
            device_serial,
            "-r",
            f"-f {frequency} --duration {duration_seconds}",
        ]

        if record_options:
            cmd[-1] = record_options

        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = (
                self.simpleperf_dir + os.pathsep + env.get("PYTHONPATH", "")
            )

            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=env,
                cwd=output_dir,
                **subprocess_hidden_window_kwargs(),
            )
            return perf_data_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Simpleperf profiling failed: {e.stderr}") from e

    def generate_html_report(self, perf_data_path: str, output_html_path: str) -> str:
        """Generates an HTML report from perf.data."""
        if not os.path.exists(self.report_html_path):
            raise FileNotFoundError(
                f"report_html.py not found at {self.report_html_path}"
            )

        if not os.path.exists(perf_data_path):
            raise FileNotFoundError(f"perf.data not found at {perf_data_path}")

        cmd = [
            sys.executable,
            self.report_html_path,
            "-i",
            perf_data_path,
            "-o",
            output_html_path,
        ]

        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = (
                self.simpleperf_dir + os.pathsep + env.get("PYTHONPATH", "")
            )

            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=env,
                **subprocess_hidden_window_kwargs(),
            )
            return output_html_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"HTML report generation failed: {e.stderr}") from e

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
