from typing import List
from easy_tracer.models import device as device_model
from easy_tracer.framework import adb_helper

class DeviceService:
    def __init__(self, adb_adapter: adb_helper.AdbHelper):
        self.adb_adapter = adb_adapter

    def get_connected_devices(self) -> List[device_model.Device]:
        """Returns a list of connected devices."""
        return self.adb_adapter.list_devices()

    def is_adb_available(self) -> bool:
        """Checks if ADB is installed and available."""
        return self.adb_adapter.is_available()
