from typing import List
from easy_tracer.models.device import Device
from easy_tracer.framework.adb_adapter import AdbAdapter

class DeviceService:
    def __init__(self, adb_adapter: AdbAdapter):
        self.adb_adapter = adb_adapter

    def get_connected_devices(self) -> List[Device]:
        """Returns a list of connected devices."""
        return self.adb_adapter.list_devices()

    def is_adb_available(self) -> bool:
        """Checks if ADB is installed and available."""
        return self.adb_adapter.is_available()
