import os
import sys
import subprocess
from typing import List, Optional
from easy_tracer.framework.subprocess_utils import subprocess_hidden_window_kwargs


class SystraceAdapter:
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path
        # Calculate path to run_systrace.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.script_path = os.path.join(
            current_dir, "external", "systrace", "systrace", "systrace", "run_systrace.py"
        )

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

        # Construct command prefix
        # If frozen, use the exe itself with --execute-script to run the python script
        # entirely within the bundled environment
        cmd_prefix = [sys.executable]
        if getattr(sys, "frozen", False):
            cmd_prefix.append("--execute-script")

        cmd = cmd_prefix + [
            self.script_path,
            "-o",
            output_file,
            "-t",
            str(time_seconds),
            "-e",
            device_serial,
        ]

        if buffer_size_kb:
            cmd.extend(["-b", str(buffer_size_kb)])

        if app_name:
            cmd.extend(["-a", app_name])

        # Add categories at the end
        cmd.extend(categories)

        try:
            # We need to set PYTHONPATH to include the external directories
            # The run_systrace.py script expects to find 'devil' and 'systrace' in path
            # But the script itself handles some of this. Let's rely on its internal logic first,
            # but we might need to adjust env if it fails.
            # However, looking at run_systrace.py, it does sys.path.insert for devil and systrace.
            # So we should be fine just running it.

            # Important: We need to make sure the environment has ADB in PATH if not already handled
            # But our AdbAdapter usually assumes 'adb' is in path.

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Systrace failed: {e.stderr}") from e

    def get_categories(self, device_serial: str) -> List[str]:
        """
        Returns a list of available categories from the device.
        """
        if not os.path.exists(self.script_path):
            raise FileNotFoundError(f"Systrace script not found at {self.script_path}")

        cmd_prefix = [sys.executable]
        if getattr(sys, "frozen", False):
            cmd_prefix.append("--execute-script")

        cmd = cmd_prefix + [self.script_path, "-l", "-e", device_serial]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
            # Parse output to get categories
            # Output format usually: "  category_name - description"
            categories = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("Category") or line.startswith("--"):
                    continue
                # Take the first part before space or hyphen
                parts = line.split()
                if parts:
                    categories.append(parts[0])
            return categories
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to list categories: {e.stderr}") from e

    def get_ftrace_events(self, device_serial: str) -> List[str]:
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
