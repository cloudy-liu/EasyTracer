from typing import List, Optional
from easy_tracer.models.device import Device
from easy_tracer.services.device_service import DeviceService

class MainPresenter:
    def __init__(self, device_service: DeviceService):
        self.device_service = device_service
        self.selected_device: Optional[Device] = None

    def get_devices(self) -> List[Device]:
        """Fetches the list of connected devices."""
        return self.device_service.get_connected_devices()

    def on_device_selected(self, device: Optional[Device]):
        """Handles device selection."""
        self.selected_device = device
        # In a real app, we might notify other parts of the app here
        print(f"Device selected: {device}")
