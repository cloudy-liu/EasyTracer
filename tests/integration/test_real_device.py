import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from easy_tracer.framework.adb_adapter import AdbAdapter
from easy_tracer.services.device_service import DeviceService

class TestRealDevice(unittest.TestCase):
    def test_get_connected_devices(self):
        print("\nTesting Real Device Connection...")
        adapter = AdbAdapter()
        service = DeviceService(adapter)

        try:
            devices = service.get_connected_devices()
        except RuntimeError as e:
             self.skipTest(f"ADB not available: {e}")
             return

        if not devices:
            print("No devices found. Skipping real device test.")
            self.skipTest("No devices connected via ADB")
            return

        print(f"Found {len(devices)} devices.")

        for dev in devices:
            print(f"Device: {dev}")

        self.assertTrue(len(devices) > 0)

if __name__ == '__main__':
    unittest.main()
