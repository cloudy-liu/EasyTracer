import subprocess
from typing import List
from easy_tracer.models.device import Device
from easy_tracer.framework.subprocess_utils import subprocess_hidden_window_kwargs


class AdbAdapter:
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path

    def _run_command(self, args: List[str]) -> str:
        """Runs an adb command and returns the output."""
        try:
            result = subprocess.run(
                [self.adb_path] + args,
                capture_output=True,
                text=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            # Check if it's just no devices found or a real error
            raise RuntimeError(f"ADB command failed: {e.stderr}") from e
        except FileNotFoundError:
            raise RuntimeError(
                f"ADB executable not found at '{self.adb_path}'. Please ensure Android SDK Platform-Tools are installed and in PATH."
            )

    def list_devices(self) -> List[Device]:
        """Lists connected devices with details."""
        devices = []
        try:
            output = self._run_command(["devices", "-l"])
        except RuntimeError:
            return []

        # Parse output line by line
        # Example output:
        # List of devices attached
        # 1234567890abcde        device product:bullhead model:Nexus_5X device:bullhead transport_id:1

        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue

            # Split by whitespace to get serial and status first
            parts = line.split()
            if len(parts) < 2:
                continue

            serial = parts[0]
            status = parts[1]

            # Parse key:value pairs for the rest
            details = {}
            for part in parts[2:]:
                if ":" in part:
                    key, value = part.split(":", 1)
                    details[key] = value

            device = Device(
                serial=serial,
                status=status,
                model=details.get("model", ""),
                product=details.get("product", ""),
                device=details.get("device", ""),
                usb=details.get("usb", ""),
                transport_id=details.get("transport_id", ""),
            )
            devices.append(device)

        return devices

    def is_available(self) -> bool:
        """Checks if ADB is available."""
        try:
            subprocess.run(
                [self.adb_path, "--version"],
                capture_output=True,
                check=True,
                **subprocess_hidden_window_kwargs(),
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
