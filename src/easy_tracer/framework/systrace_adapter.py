import os
import sys
import io
import contextlib
import importlib.util
from typing import List, Optional


class SystraceAdapter:
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # New simplified structure: external/systrace/systrace.py is the entry point
        self.systrace_root = os.path.join(current_dir, "external", "systrace")
        self.script_path = os.path.join(self.systrace_root, "systrace.py")

    def _import_and_run_systrace(self, args: List[str]) -> str:
        """
        Dynamically imports systrace.py and runs its main_impl with args.
        Captures and returns stdout.
        """
        # Ensure sys.path has the systrace root for imports
        if self.systrace_root not in sys.path:
            sys.path.insert(0, self.systrace_root)

        # Import systrace module
        spec = importlib.util.spec_from_file_location("systrace", self.script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load systrace from {self.script_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["systrace"] = module
        spec.loader.exec_module(module)

        # Capture output
        output_capture = io.StringIO()

        try:
            with contextlib.redirect_stdout(output_capture), contextlib.redirect_stderr(output_capture):
                try:
                    # main_impl expects argv where argv[0] is script name
                    module.main_impl(["systrace.py"] + args)
                except SystemExit as e:
                    if e.code != 0 and e.code is not None:
                        raise RuntimeError(f"Systrace exited with code {e.code}")
        except Exception as e:
            captured = output_capture.getvalue()
            raise RuntimeError(f"Systrace failed: {str(e)}\nLog: {captured}")

        return output_capture.getvalue()

    def run_systrace(
        self,
        output_file: str,
        time_seconds: int,
        device_serial: str,
        categories: List[str],
        buffer_size_kb: Optional[int] = None,
        app_name: Optional[str] = None,
    ) -> str:
        """
        Runs systrace with the given parameters.
        Returns the output (stdout) of the command.
        """
        if not os.path.exists(self.script_path):
            raise FileNotFoundError(f"Systrace script not found at {self.script_path}")

        args = [
            "-o", output_file,
            "-t", str(time_seconds),
            "-e", device_serial,
        ]

        if buffer_size_kb:
            args.extend(["-b", str(buffer_size_kb)])

        if app_name:
            args.extend(["-a", app_name])

        # Add categories at the end
        args.extend(categories)

        return self._import_and_run_systrace(args)

    def get_categories(self, device_serial: str) -> List[str]:
        """
        Returns a list of available categories from the device.
        """
        if not os.path.exists(self.script_path):
            raise FileNotFoundError(f"Systrace script not found at {self.script_path}")

        args = ["-l", "-e", device_serial]

        output = self._import_and_run_systrace(args)

        # Parse output to get categories
        # Output format usually: "  category_name - description"
        categories = []
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("Category") or line.startswith("--"):
                continue
            # Take the first part before space or hyphen
            parts = line.split()
            if parts:
                categories.append(parts[0])
        return categories

    def get_ftrace_events(self, device_serial: str) -> List[str]:
        import subprocess
        from easy_tracer.framework.subprocess_utils import subprocess_hidden_window_kwargs

        cmd = [
            self.adb_path,
            "-s",
            device_serial,
            "shell",
            "cat",
            "/sys/kernel/tracing/available_events",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
            events = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                events.append(line)
            return events
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to list ftrace events: {e.stderr}") from e
