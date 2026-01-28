import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.adb_adapter import AdbAdapter

class TestAdbAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = AdbAdapter()

    @patch('subprocess.run')
    def test_list_devices_success(self, mock_run):
        # Mock successful adb devices -l output
        mock_output = """List of devices attached
1234567890abcde        device product:bullhead model:Nexus_5X device:bullhead transport_id:1
"""
        mock_run.return_value = MagicMock(
            stdout=mock_output,
            returncode=0
        )

        devices = self.adapter.list_devices()

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].serial, "1234567890abcde")
        self.assertEqual(devices[0].status, "device")
        self.assertEqual(devices[0].model, "Nexus_5X")

    @patch('subprocess.run')
    def test_list_devices_empty(self, mock_run):
        mock_output = "List of devices attached\n"
        mock_run.return_value = MagicMock(
            stdout=mock_output,
            returncode=0
        )

        devices = self.adapter.list_devices()
        self.assertEqual(len(devices), 0)

    @patch('subprocess.run')
    def test_is_available_true(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(self.adapter.is_available())

    @patch('subprocess.run')
    def test_is_available_false(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        self.assertFalse(self.adapter.is_available())

if __name__ == '__main__':
    unittest.main()
