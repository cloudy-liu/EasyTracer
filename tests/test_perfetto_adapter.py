import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from easy_tracer.framework.perfetto_adapter import PerfettoAdapter
from easy_tracer.framework.adb_helper import AdbHelper


class TestPerfettoAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_adb = MagicMock(spec=AdbHelper)
        self.mock_adb.run_shell.return_value = ""
        self.adapter = PerfettoAdapter(adb=self.mock_adb)

    def test_record_trace_success(self):
        device_serial = "12345"
        output_path = "local.trace"

        path = self.adapter.record_trace(
            device_serial=device_serial,
            output_path=output_path,
            duration_seconds=5
        )

        self.assertEqual(path, output_path)

        # Verify run_shell called for perfetto command
        run_shell_calls = [c for c in self.mock_adb.run_shell.call_args_list]
        self.assertGreaterEqual(len(run_shell_calls), 1)

        # First call should be perfetto command
        first_call_args = run_shell_calls[0][0]
        self.assertEqual(first_call_args[0], device_serial)
        # Args should contain perfetto command parts
        call_str = " ".join(str(a) for a in first_call_args[1:])
        self.assertIn("perfetto", call_str)
        self.assertIn("-t", call_str)
        self.assertIn("5s", call_str)

        # Verify pull_file called
        self.mock_adb.pull_file.assert_called_once()
        pull_args = self.mock_adb.pull_file.call_args[0]
        self.assertEqual(pull_args[0], device_serial)
        self.assertEqual(pull_args[2], output_path)

        # Verify remove_file called for cleanup
        self.mock_adb.remove_file.assert_called_once()


if __name__ == '__main__':
    unittest.main()
