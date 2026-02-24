"""ADB helper: device discovery, availability checks, and device property queries."""

from __future__ import annotations

from typing import List

from easy_tracer.framework import subprocess_utils
from easy_tracer.models import device as device_model


class AdbHelper:
    def __init__(self, adb_path: str = "adb") -> None:
        self.adb_path = adb_path

    def _run(self, args: List[str]) -> str:
        return subprocess_utils.check_output([self.adb_path, *args])

    def list_devices(self) -> List[device_model.Device]:
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

    def _get_prop(self, device_serial: str, prop: str) -> str:
        """Read a single Android property and normalize empty/unknown values."""
        try:
            value = subprocess_utils.check_output(
                [self.adb_path, "-s", device_serial, "shell", "getprop", prop]
            ).strip()
        except Exception:
            return ""
        if not value:
            return ""
        if value.lower() in {"unknown", "null", "none", "n/a"}:
            return ""
        return value

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
