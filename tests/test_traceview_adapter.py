import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.traceview_adapter import TraceviewAdapter
from easy_tracer.framework.adb_helper import AdbHelper


class TestTraceviewAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_adb = MagicMock(spec=AdbHelper)
        self.mock_adb.run_shell.return_value = ""
        self.adapter = TraceviewAdapter(adb=self.mock_adb)

    def test_start_tracing_default(self):
        device_serial = "123"
        package = "com.example"

        self.adapter.start_tracing(device_serial, package)

        self.mock_adb.run_shell.assert_called_once()
        args = self.mock_adb.run_shell.call_args[0]
        self.assertEqual(args[0], device_serial)

        # Command args should contain am profile start
        cmd_parts = args[1:]
        self.assertIn("am", cmd_parts)
        self.assertIn("profile", cmd_parts)
        self.assertIn("start", cmd_parts)
        self.assertIn(package, cmd_parts)
        # Verify no sampling flag
        self.assertNotIn("--sampling", cmd_parts)

    def test_start_tracing_sampling(self):
        self.adapter.start_tracing("123", "com.example", sampling=True, sampling_interval=1000)

        args = self.mock_adb.run_shell.call_args[0]
        cmd_parts = args[1:]
        self.assertIn("--sampling", cmd_parts)
        self.assertIn("1000", cmd_parts)

    @patch('time.sleep')
    def test_stop_tracing_success(self, mock_sleep):
        output_path = "trace.trace"
        path = self.adapter.stop_tracing("123", "com.example", output_path)

        self.assertEqual(path, output_path)

        # Verify run_shell called for stop command
        stop_call = self.mock_adb.run_shell.call_args_list[0]
        stop_args = stop_call[0]
        self.assertEqual(stop_args[0], "123")
        self.assertIn("stop", stop_args)

        # Verify pull_file called
        self.mock_adb.pull_file.assert_called_once()
        pull_args = self.mock_adb.pull_file.call_args[0]
        self.assertEqual(pull_args[2], output_path)

        # Verify remove_file called for cleanup
        self.mock_adb.remove_file.assert_called_once()


if __name__ == '__main__':
    unittest.main()
