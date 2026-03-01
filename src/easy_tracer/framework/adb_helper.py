"""ADB helper: unified interface for all ADB operations.

Single source of truth for:
- Device discovery and availability checks
- Property queries with caching
- Shell command execution
- File transfer (pull/push/remove)
- Auxiliary dump commands
"""

from __future__ import annotations

import logging

from easy_tracer.framework import subprocess_utils
from easy_tracer.models import device as device_model

logger = logging.getLogger(__name__)


class AdbHelper:
    def __init__(self, adb_path: str = "adb") -> None:
        self.adb_path = adb_path
        self._prop_cache: dict[str, dict[str, str]] = {}  # device_serial -> {prop: value}

    def _run(self, args: list[str], timeout: int | None = None) -> str:
        return subprocess_utils.check_output([self.adb_path, *args], timeout=timeout)

    def list_devices(self) -> list[device_model.Device]:
        """Lists connected devices with details."""
        try:
            output = self._run(["devices", "-l"])
        except RuntimeError:
            return []

        devices = []
        for line in output.split("\n"):
            line = line.strip()
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            status = parts[1]
            details: dict[str, str] = {}
            for part in parts[2:]:
                if ":" in part:
                    key, value = part.split(":", 1)
                    details[key] = value
            devices.append(
                device_model.Device(
                    serial=serial,
                    status=status,
                    model=details.get("model", ""),
                    product=details.get("product", ""),
                    device=details.get("device", ""),
                    usb=details.get("usb", ""),
                    transport_id=details.get("transport_id", ""),
                )
            )
        return devices

    def is_available(self) -> bool:
        """Checks if ADB is available."""
        try:
            subprocess_utils.check_output([self.adb_path, "--version"], timeout=5)
            return True
        except RuntimeError:
            return False

    # =========================================================================
    # PROPERTY QUERIES (WITH CACHING)
    # =========================================================================

    def _get_prop(self, device_serial: str, prop: str) -> str:
        """Read a single Android property with caching and normalization."""
        if not device_serial:
            return ""

        cache = self._prop_cache.setdefault(device_serial, {})
        if prop in cache:
            return cache[prop]

        try:
            value = self.run_shell(device_serial, "getprop", prop).strip()
        except Exception:
            value = ""

        if value.lower() in {"unknown", "null", "none", "n/a", ""}:
            value = ""

        cache[prop] = value
        return value

    def get_sdk_version(self, device_serial: str) -> int:
        """Get device SDK version (cached)."""
        sdk_str = self._get_prop(device_serial, "ro.build.version.sdk")
        if not sdk_str:
            return -1
        try:
            return int(sdk_str.split()[-1])  # Handle extra adb output
        except (ValueError, IndexError):
            return -1

    def clear_cache(self, device_serial: str | None = None) -> None:
        """Clear property cache for a device or all devices."""
        if device_serial:
            self._prop_cache.pop(device_serial, None)
        else:
            self._prop_cache.clear()

    # =========================================================================
    # SHELL COMMAND EXECUTION
    # =========================================================================

    def run_shell(self, device_serial: str, *args: str, timeout: int | None = None) -> str:
        """Run shell command on device and return output.

        Args:
            device_serial: Target device serial.
            *args: Shell command arguments (will be joined with spaces).
            timeout: Optional timeout in seconds.

        Returns:
            Command output as string.
        """
        shell_cmd = " ".join(args)
        return self._run(["-s", device_serial, "shell", shell_cmd], timeout=timeout)

    def run_shell_with_status(
        self, device_serial: str, *args: str
    ) -> tuple[str, int]:
        """Run shell command and return (output, return_code).

        Useful for commands where non-zero exit may be expected.
        """
        shell_cmd = " ".join(args)
        cmd = [self.adb_path, "-s", device_serial, "shell", shell_cmd]
        try:
            output = subprocess_utils.check_output(cmd)
            return output, 0
        except Exception as e:
            return str(e), 1

    # =========================================================================
    # FILE TRANSFER
    # =========================================================================

    def pull_file(self, device_serial: str, device_path: str, local_path: str) -> None:
        """Pull file from device to local filesystem."""
        self._run(["-s", device_serial, "pull", device_path, local_path])

    def push_file(self, device_serial: str, local_path: str, device_path: str) -> None:
        """Push file from local filesystem to device."""
        self._run(["-s", device_serial, "push", local_path, device_path])

    def remove_file(self, device_serial: str, device_path: str) -> None:
        """Remove file on device (best-effort, silent on failure)."""
        try:
            self.run_shell(device_serial, "rm", device_path)
        except Exception:
            pass

    def get_device_model(self, device_serial: str) -> str:
        """Returns a stable device display name with fallbacks.

        Fallback order references the TMP/original project strategy:
        ro.product.model -> ro.product.name -> ro.product.device.
        """
        if not device_serial:
            return ""

        # Primary + compatibility fallbacks (some OEM ROMs leave model empty).
        for prop in (
            "ro.product.model",
            "ro.product.name",
            "ro.product.device",
        ):
            value = self._get_prop(device_serial, prop)
            if value:
                return value

        # Last resort: parse adb devices -l details for this serial.
        for dev in self.list_devices():
            if dev.serial == device_serial:
                for value in (dev.model, dev.product, dev.device):
                    if value:
                        return value
                break
        return ""

    # =========================================================================
    # AUXILIARY DUMP COMMANDS
    # =========================================================================

    def dump_logcat(self, device_serial: str, output_path: str) -> str:
        """Dumps device logcat (all buffers) to a file."""
        output = self._run(["-s", device_serial, "logcat", "-b", "all", "-d"])
        with open(output_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(output)
        return output_path

    def dump_packages(self, device_serial: str, output_path: str) -> str:
        """Dumps package manager state to a file."""
        output = self._run(["-s", device_serial, "shell", "dumpsys", "package"])
        with open(output_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(output)
        return output_path

    def dump_ps(self, device_serial: str, output_path: str) -> str:
        """Dumps process list with thread info to a file."""
        output = self._run(["-s", device_serial, "shell", "ps", "-AT"])
        with open(output_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(output)
        return output_path

    def dump_meminfo(self, device_serial: str, output_path: str) -> str:
        """Dumps memory info to a file."""
        output = self._run(["-s", device_serial, "shell", "dumpsys", "meminfo"])
        with open(output_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(output)
        return output_path
