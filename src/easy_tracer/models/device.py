from dataclasses import dataclass

@dataclass
class Device:
    serial: str
    status: str  # e.g., 'device', 'offline', 'unauthorized'
    model: str = ""
    product: str = ""
    device: str = ""
    usb: str = ""
    transport_id: str = ""

    def __str__(self) -> str:
        if self.model:
            return f"{self.model} ({self.serial})"
        return self.serial
